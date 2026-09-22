#!/bin/sh

SECURE_HOME=/opt/roche/var/lib/rlx-secure-boot

# FIXME: do not use /tmp, use ram disk
TMP=$(mktemp -d)
TMP_GRUB_CFG=$TMP/grub.cfg
TMP_GRUB_EFI=$TMP/grubx64.efi

if [ -f /opt/roche/lib/rlx-secure-boot/secure-boot.inc.sh ]; then
    . /opt/roche/lib/rlx-secure-boot/secure-boot.inc.sh
fi

GRUBMODULES="part_gpt fat"                             # partition and file systems for EFI
GRUBMODULES="$GRUBMODULES echo normal linux linuxefi"  # boot linux
GRUBMODULES="$GRUBMODULES efi_uga all_video"           # video output
GRUBMODULES="$GRUBMODULES search search_fs_uuid"       # search --fs-uuid
GRUBMODULES="$GRUBMODULES password_pbkdf2"             # hashed password
GRUBMODULES="$GRUBMODULES $EXTRA_GRUBMODULES"          # append additional modules from hook

clearbootentries=0
if [ "$1" = "clearbootentries" ]; then
    clearbootentries=1
fi

projectname=$(cut -d/ -f1 /opt/roche/etc/projectinfo)
if [ -e /opt/roche/etc/project-version ]; then  # customer project
    projectversion=`cat /opt/roche/etc/project-version`
elif [ -e /opt/roche/etc/rlx-version ]; then  # rlxprj
    projectversion=`cat /opt/roche/etc/rlx-version`
elif [ -e /opt/roche/etc/rlx-project-release ]; then  # obsolete
    projectversion=`cat /opt/roche/etc/rlx-project-release`
fi
efidev=$(grep -w /boot/efi /proc/mounts | cut -d' ' -f1)
PART_EFI_UUID=$(blkid -s UUID -o value $efidev)
bootid=`cat /.rlx-bootid`

escape_for_sed() {
    printf '%s' "$1" | sed 's!/!\\/!g'
}

create_efi_grub()
{
    . /etc/default/grub
    root_part_type=`lsblk -l -n -o TYPE,MOUNTPOINT -p | grep '/$' | cut -d' ' -f1`
    if [ -z "$root_part_type" ]; then  # try btrfs
        root_part_type=`grep ' / ' /proc/mounts | cut -d' ' -f3`
    fi
    if [ "$root_part_type" = "lvm" ]; then
        vg_name=`vgs --noheadings | awk '{print $1}' | sed s/-/--/g`
        root_cmdline=$(escape_for_sed "root=/dev/mapper/$vg_name-root ro")
    elif [ "$root_part_type" = "btrfs" ]; then
        root_part=`grep ' / ' /proc/mounts | cut -d' ' -f1`
        root_uuid=`blkid $root_part -o export | grep '^UUID='`
        root_cmdline=$(escape_for_sed "root=$root_uuid rootflags=subvol=root ro")
    else # standard partitioning
        root_part=`lsblk -l -n -o NAME,MOUNTPOINT -p | grep '/$' | cut -d' ' -f1`
        root_uuid=`blkid $root_part -o export | grep '^UUID='`
        root_cmdline=$(escape_for_sed "root=$root_uuid ro")
    fi

    default_cmdline="$(escape_for_sed """$GRUB_CMDLINE_LINUX_DEFAULT $GRUB_CMDLINE_LINUX""" | sed s_\\\$_\\\\\$_)"
    LINUX_CMDLINE="$root_cmdline $default_cmdline"

    if [ -z "$GRUBTMPL" ]; then
        GRUBTMPL="/opt/roche/share/rlx-osal/grub.cfg.tmpl"
    fi

    # create random password for grub menu
    random_pass=$(head -c 99 /dev/urandom | base64 -w0 -)

    # sending via echo is not supported since bookworm
    pass_hash=$(cat << EOF | grub-mkpasswd-pbkdf2 | awk '/grub.pbkdf/{print$NF}'
$random_pass
$random_pass
EOF
)


    sed -e "s/@@PART_EFI_UUID@@/$PART_EFI_UUID/" \
        -e "s/@@BOOTID@@/$bootid/" \
        -e "s/@@PROJECT@@/$projectname/" \
        -e "s/@@VERSION@@/$projectversion/" \
        -e "s/@@LINUX_CMDLINE@@/$LINUX_CMDLINE/" \
        -e "s/@@GRUB_PBKDF2@@/$pass_hash/" \
        $GRUBTMPL > $TMP_GRUB_CFG

    mkdir -p /boot/efi/EFI/rlx

    if [ -n "$RLX_SECURE_BOOT" ]; then
        sign_kernel_initrd
    fi

    for kernel in /boot/vmlinuz-*; do
        cp $kernel /boot/efi/EFI/rlx/${bootid}_${projectname}_$projectversion.vmlinuz
    done
    for initrd in /boot/initrd.img-*; do
        cp $initrd /boot/efi/EFI/rlx/${bootid}_${projectname}_$projectversion.initrd
    done

    if [ -n "$RLX_SECURE_BOOT" ]; then
        make_efi_grub
    else
        grub-mkstandalone \
            --directory /usr/lib/grub/x86_64-efi \
            --format x86_64-efi \
            --modules "$GRUBMODULES" \
            --output "$TMP_GRUB_EFI" \
            "boot/grub/grub.cfg=$TMP_GRUB_CFG"
    fi

    if [ -n "$RLX_SECURE_BOOT" ]; then
        sign_efi_grub $TMP_GRUB_EFI
    fi

    TARGET_EFI=/boot/efi/EFI/rlx/${bootid}_${projectname}_$projectversion.efi
    cp $TMP_GRUB_EFI $TARGET_EFI

    # to support systems which do not have custom efi boot order (eg H3C in CDP)
    mkdir -p /boot/efi/EFI/BOOT
    cp -f $TMP_GRUB_EFI /boot/efi/EFI/BOOT/BOOTX64.EFI
}

create_efi_entries()
{
    # remove old bootentries if requested
    if [ $clearbootentries -eq 1 ]; then
        pbootids=`efibootmgr | grep -e "^Boot[0-9A-Fa-f]\+" | grep -v "^BootCurrent" | grep -w $projectname | sed -n 's/^Boot0*\([0-9A-Fa-f]\+\).*/\1/p'`
        for bid in $pbootids
        do
            efibootmgr -B -b $bid
        done
    fi

    bootids_hex=`efibootmgr | sed -n 's/^Boot0*\([0-9A-Fa-f]\+\).*/\1/p'`
    bootids=
    for bid in $bootids_hex
    do
        bootids=$bootids" "`echo "ibase=16; $bid" | busybox bc` # convert to decimal
    done

    bootentry=0
    while echo $bootids | grep -q -w $bootentry
    do
        bootentry=$((bootentry+1))
    done
    bootentry=`echo "obase=16; $bootentry" | busybox bc` # convert to hex

    efipart=`grep -w /boot/efi /proc/mounts | cut -d' ' -f1 | xargs basename`
    efipartno=`cat /sys/class/block/$efipart/partition`
    efidisk="/dev/`readlink /sys/class/block/$efipart | xargs dirname | xargs basename`"

    label="$projectname $projectversion"

    # check if label already exists
    labels=`efibootmgr | sed -n 's/^Boot0[0-9A-Fa-f\*]\+ //p' | tr ' ' '#'`
    origlabel=$label
    if echo $labels | grep -q -w `echo $label | tr ' ' '#'`; then
        label="$origlabel ($bootid)"
    fi

    efibootmgr -c -b $bootentry -l "EFI\\rlx\\${bootid}_${projectname}_$projectversion.efi" \
               -L "$label" -d $efidisk -p $efipartno -o $bootentry

    bootidfile=/boot/efi/rlx-boot$bootid
    cat > $bootidfile <<EOF
BOOTID=$bootid
BOOTENTRY=$bootentry
PROJECTNAME=$projectname
PROJECTVERSION=$projectversion
EOF
    echo -n BOOTID=$bootid > /boot/efi/rlx-current

    rm -rf $TMP
}

create_efi_grub
create_efi_entries
