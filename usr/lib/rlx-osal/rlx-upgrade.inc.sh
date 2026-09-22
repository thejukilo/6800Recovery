#!/bin/sh

log_error()
{
    echo "*E: $@" >&2
    if grep -q "splash" /proc/cmdline; then
        plymouth display-message --text="[Roche-upgrade] * $@" || true
    fi
    exit 1
}

log_warning()
{
    echo "*W: $@" >&2
    if grep -q "splash" /proc/cmdline; then
        plymouth display-message --text="[Roche-upgrade] * $@" || true
    fi
}

log_info()
{
    echo "*I: $@"
    if grep -q "splash" /proc/cmdline; then
        plymouth display-message --text="[Roche-upgrade] * $@" || true
    fi
}

log_notice()
{
    echo "*N: $@"
    if grep -q "splash" /proc/cmdline; then
        plymouth display-message --text="[Roche-upgrade]$@" || true
    fi
}

plymouth_upgrade_progress()
{
    if grep -q "splash" /proc/cmdline; then
        plymouth system-update --progress=$1 || true
    fi
}

extract_archive()
{
    mkdir -p $WORK_DIR/archive
    tar --owner=roche --mode=600 -C $WORK_DIR/archive -xf $UPGRADE_ARCHIVE
    if [ $? -ne 0 ]; then
        log_error "Error extracting upgrade archive"
    fi
    df -k | grep ^/dev
    rm -f $UPGRADE_ARCHIVE
}

verify_signature()
{
    file=sha256.sums
    test `passwd -S roche | cut -d ' ' -f2` = 'P'
    user_is_locked=$?  # 1 - locked, if no password (prod) or locked, 0 - not locked, if password set (dev, test)
    if [ ! -f $WORK_DIR/archive/$file.signature ]; then  # no signature file found
        if [ $user_is_locked -eq 0 ]; then
            log_warning "Warning: accepting missing signature, roche account is not locked"
        else
            log_error "Error: no signature found in upgrade archive"
        fi
    else
        /opt/roche/sbin/ssl-verify.sh $WORK_DIR/archive/$file $WORK_DIR/archive/$file.signature
        if [ $? -ne 0 ]; then
            if [ $user_is_locked -eq 0 ]; then
                log_warning "Warning: accepting wrong signature, roche account is not locked"
            else
                log_error "Error: invalid signature in upgrade archive"
            fi
        fi
        rm -f $WORK_DIR/archive/$file.signature
    fi
}

verify_checksums()
{
    cd $WORK_DIR/archive
    awk '{ print $2 }' sha256.sums | xargs sha256sum > $WORK_DIR/sha256.sums.check
    RET=$?
    cd - >/dev/null
    if [ $RET -ne 0 ]; then
        log_error "Error: sha256sum"
    fi

    diff $WORK_DIR/sha256.sums.check $WORK_DIR/archive/sha256.sums > /dev/null
    if [ $? -ne 0 ]; then
        log_error "Error: archive checksum mismatch"
    fi
    rm -f $WORK_DIR/archive/sha256.sums
}

verify_upgrade()
{
    mv -f $WORK_DIR/archive/file.list $WORK_DIR/file.list.orig
    if [ $? -ne 0 ]; then
        log_error "Error moving file.list"
    fi
    cd $WORK_DIR/archive
    find -type f -exec stat -c "%n %s" {} \; | LC_ALL=C sort > ../file.list
    cd - >/dev/null
    diff $WORK_DIR/file.list.orig $WORK_DIR/file.list > /dev/null
    if [ $? -ne 0 ]; then
        log_error "Error: diff file.list mismatch"
    fi

    if ! grep -q -w `cat /opt/roche/etc/projectinfo` $WORK_DIR/archive/baseversion; then
        log_error "Error: upgrade package is for version `cat $WORK_DIR/archive/baseversion`"
    fi
}

verify_toplevel_package()
{
    # The required top-level package that needs to be installed on the system before proceeding with the upgrade
    required_package_file="$WORK_DIR/archive/toplevel-package"

    if [ -f "$required_package_file" ]; then
        required_package=$(cat "$required_package_file")
        if ! dpkg -s "$required_package" 1>/dev/null 2>/dev/null; then
            log_info "Aborting upgrade"
            log_error "Error: top-level package mismatch. Package '$required_package' is not installed"
        fi
        log_info "Required top-level package '$required_package' is installed"
    else
        log_info "Required package file '$required_package_file' not found"
        log_info "Proceeding with the upgrade without verifying top-level package match"
    fi
}

docker_down()
{
    cd /opt/roche/var/lib/docker-compose/
    docker-compose --no-ansi -f /opt/roche/etc/docker-compose.yml stop -t 300 2>&1
    if [ $? -ne 0 ]; then
        log_warning "Error running docker-compose stop"
    fi
    docker-compose --no-ansi -f /opt/roche/etc/docker-compose.yml down -t 300 2>&1
    if [ $? -ne 0 ]; then
        log_error "Error running docker-compose down"
    fi
}

verify_diskspace()
{
    if [ -n "$UPGRADE_MINFREE" ]; then
        mbytes=`df -m /opt | awk '{ print $4 }' | tail -n1`
        if [ $mbytes -lt $UPGRADE_MINFREE ]; then
            log_error "Error not enough disk space for upgrading the system"
            exit 1
        fi
    fi
}

docker_envbackup()
{
    # Create a backup of current user configured docker env variables
    envfile=/opt/roche/var/lib/docker-compose/.env

    if [ -f $envfile ]; then
      cp $envfile $WORK_DIR/old.env
    fi
}

docker_reduplicate()
{
    if [ ! -f $WORK_DIR/archive/docker-containers.dedup.tar ]; then
        return
    fi

    oldimages=`grep -v -P '^[ \t]*#' /opt/roche/etc/docker-compose.yml | grep "image:" | awk '{ print $2 }' | LC_ALL=C sort`
    if [ -f /opt/roche/var/lib/docker-compose/.env ]; then
        # Disable output logging as the variables might contain secrets which
        # must not be visible in the upgrade log
        set +x

        oldimages=`. /opt/roche/var/lib/docker-compose/.env; for i in $oldimages; do eval echo $i; done`

        set -x
    fi
    docker save $oldimages > $WORK_DIR/archive/docker-containers.old.tar
    curdir=`pwd`
    cd $WORK_DIR/archive
    old_tar=$WORK_DIR/archive/docker-containers.old.tar
    dedup_tar=$WORK_DIR/archive/docker-containers.dedup.tar
    out_tar=$WORK_DIR/archive/docker-containers.tar
    mkdir -p $WORK_DIR/dedupwork/old $WORK_DIR/dedupwork/new

    # extract old container images
    cd $WORK_DIR/dedupwork/old
    tar -mp --delay-directory-restore -xf $old_tar
    # convert symlinks to hardlinks (shared leayers)
    find . -type l -exec sh -c 'mv {} {}.old; ln `readlink {}.old | cut -d/ -f2-` {}; rm -f {}.old' \;
    df -k | grep ^/dev
    rm -f $old_tar
    cd ..

    # extract dedup container images
    cd new
    tar -mp --delay-directory-restore -xf $dedup_tar
    mv deduplicated.files ../
    df -k | grep ^/dev
    rm -f $dedup_tar
    cd ../..

    set +x
    dedups=`cat dedupwork/deduplicated.files`
    old_IFS="$IFS"
    IFS="
" # IFS is newline

    input=""
    output=""
    for entry in $dedups
    do
        case $entry in
            I*)
                input="${entry#I}"
                ;;
            O*)
                ln $input "${entry#O}"
		if [ "$?" -ne 0 ]; then
		    log_error "Error reduplication docker images"
		    exit 1
                fi
                ;;
        esac
    done
    set -x

    IFS=$old_IFS

    cd dedupwork/new
    tar cf $out_tar .
    cd $curdir
    df -k | grep ^/dev
    rm -rf $WORK_DIR/dedupwork
}

rm_kernel_headers()
{
    kernel_ver=$1
    if dpkg -s linux-headers-$kernel_ver 1>/dev/null 2>/dev/null; then
        dpkg -P linux-headers-$kernel_ver
        if [ -d /lib/modules/$kernel_ver ]; then
            rm -rf /lib/modules/$kernel_ver
        fi
    fi
}

# prior to dist-upgrade, remove other kernels than current one
rm_leftover_kernel()
{
    current_ver=`uname -r`
    for kernel in /boot/vmlinuz-*; do
        kernel_ver=`echo $kernel | cut -d- -f2-`
        if [ "$current_ver" = "$kernel_ver" ]; then
            continue
        fi
        kernel_pkg=`dpkg -S $kernel | cut -d: -f1`
        ln -sf /bin/true /usr/local/bin/linux-check-removal
        dpkg -P $kernel_pkg
        rm_kernel_headers $kernel_ver
        rm -f /usr/local/bin/linux-check-removal
    done
}

# after dist-upgrade, remove old kernel only, if we have a newer one installed
rm_old_kernel()
{
    current_ver=`uname -r`
    for kernel in /boot/vmlinuz-*; do
        kernel_ver=`echo $kernel | cut -d- -f2-`
        if [ "$current_ver" = "$kernel_ver" ]; then
            continue
        fi
        # if we found any other kernel than current one it means we have newer kernel already and we can cleanup old one
        kernel_pkg=`dpkg -S /boot/vmlinuz-$current_ver | cut -d: -f1`
        ln -sf /bin/true /usr/local/bin/linux-check-removal
        dpkg -P $kernel_pkg
        rm_kernel_headers $current_ver
        rm -f /usr/local/bin/linux-check-removal
    done
}

apt_upgrade()
{
    # move main source list
    test ! -e /etc/apt/sources.list || mv -f /etc/apt/sources.list /etc/apt/sources.list.save

    # copy the new temporary source list
    if ! sed "s#@REPO_PATH@#$WORK_DIR/archive#g" $WORK_DIR/archive/debian/apt_sources_*.list > /etc/apt/sources.list ; then
        log_error "no apt source list found in the apt offline update archive"
        exit 3
    fi

    export DEBIAN_FRONTEND=noninteractive
    # Ignore sources.list.d/* files
    apt-get -qy update -o Dir::Etc::SourceParts=/non-existing-dir || exit 4

    plymouth_upgrade_progress 30

    ignored_cmds="insmode invoke-rc.d modprobe rmmod service start-stop-daemon sysctl"
    for ignore in $ignored_cmds
    do
        ln -s /bin/true /usr/local/bin/$ignore
    done

      # Disable daemons in chroot
  cat > /usr/sbin/policy-rc.d <<EOM
#!/bin/sh
while true; do
    case "\$1" in
      -*) shift ;;
      makedev|x11-common) exit 0;;
      *) exit 101;;
    esac
done
EOM
    chmod +x /usr/sbin/policy-rc.d

    rm_leftover_kernel
    plymouth_upgrade_progress 40

    apt-get -qy -f dist-upgrade
    ret=$?

    if [ $ret -eq 0 ]; then
      plymouth_upgrade_progress 65
      apt-get -qy autoremove --purge || exit 6

      rm_old_kernel

      apt-get -qy clean || exit 7

      plymouth_upgrade_progress 75
    fi

    # Undo disabling daemons
    rm -f /usr/sbin/policy-rc.d
    for ignore in $ignored_cmds
    do
        rm -f /usr/local/bin/$ignore
    done

    rm -rf /var/cache/apt/archives/*
    rm -rf /var/lib/apt/lists/*

    if [ $ret -ne 0 ]; then
        exit 5
    fi
}

docker_upgrade()
{
    df -k | grep ^/dev
    docker load -i $WORK_DIR/archive/docker-containers.tar
    if [ $? -ne 0 ]; then
        log_error "Error loading docker containers, consider using the DOCKER_UPGRADE_NO_DEDUP option in an upgrade package configuration file."
    fi
    df -k | grep ^/dev
    rm -f $WORK_DIR/archive/docker-containers.tar

    # Restore user configured environment variables if a backup exists
    if [ -f $WORK_DIR/old.env ]; then
        envfile=/opt/roche/var/lib/docker-compose/.env
        default_envfile=/opt/roche/etc/docker-compose.env

        # Create a new .env file based on the non-user entries in the new
        # docker-compose.yml file, i.e. delete all user-configurable entries
        # in the copy of the default file
        sed '/^[A-Z][0-9]\+_/d' $default_envfile > $envfile

        # Collect names of all variables which can be configured by the user,
        # i.e. XYZ=${A1_SOME_VAR_NAME}, from the new `docker-compose.yml
        vars=$(sed -n "s/.\+\${\([A-Z0-9_]\+\)}.*/\1/p" /opt/roche/etc/docker-compose.yml | LC_ALL=C sort | uniq)

        # Disable output logging as the variables might contain secrets which
        # must not be visible in the upgrade log
        set +x

        for var in $vars; do
            # Try to find the value for the variable in the backup file
            envval=$(grep -m1 "^$var=" $WORK_DIR/old.env | cut -d= -f2)

            # If it wasn't configured before load the default value
            if [ -z "$envval" ]; then
                envval=$(grep -m1 "^$var=" $default_envfile | cut -d= -f2)
            fi

            echo "$var=$envval" >> $envfile
        done

        set -x

        chown roche $envfile
    fi

    if [ -f "/opt/roche/etc/rlx-upgrade" ]; then
        . /opt/roche/etc/rlx-upgrade
    fi

    if [  -n "$RLX_UPGRADE_SKIP_DOCKER_CLEANUP" ] && [ "$RLX_UPGRADE_SKIP_DOCKER_CLEANUP" -eq 1 ]; then
        echo "Skipping docker cleanup"
    else
        cd /opt/roche/var/lib/docker-compose/
        docker-compose --no-ansi -f /opt/roche/etc/docker-compose.yml up --no-start
        if [ $? -ne 0 ]; then
            log_error "Error runnning docker-compose up"
        fi

        # start containers on next startup
        rm -f /opt/roche/var/lib/docker-compose/started

        docker image prune -a -f
        if [ $? -ne 0 ]; then
            log_warning "running docker image prune failed" >&2
        fi

        docker volume prune -f
        if [ $? -ne 0 ]; then
            log_warning "running docker volume prune failed" >&2
        fi
    fi
}

cleanup_efi_files()
{
    rm /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.efi
    if [ -f /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.initrd ]; then
        rm /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.initrd
    fi
    if [ -f /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.vmlinuz ]; then
        rm /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.vmlinuz
    fi
    if [ -f /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.vmlinuz.sig ]; then
        rm /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.vmlinuz.sig
    fi
    if [ -f /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.initrd.sig ]; then
        rm /boot/efi/EFI/rlx/${BOOTID}_${PROJECTNAME}_$PROJECTVERSION.initrd.sig
    fi
}

finalize_upgrade()
{

    if [ -f $WORK_DIR/archive/projectversion ]; then
        cp -f $WORK_DIR/archive/projectversion /opt/roche/etc/projectinfo
        if [ $? -ne 0 ]; then
            log_error "Error update projectinfo file"
        fi
    fi

    if [ -d /sys/firmware/efi ]; then
        if [ $KEEP_CURRENT_VERSION -eq 0 ]; then # remove existing boot entry and efi files
            bootid=`cat /.rlx-bootid`
            bootidfile=/boot/efi/rlx-boot$bootid
            . $bootidfile # still contains info about current system
            efibootmgr -B -b $BOOTENTRY
            if [ -f /opt/roche/etc/.keepupgradesnapshot ]; then # only if we do keep upgrade snapshot for manual rollback
                cp $bootidfile /boot/efi/rlx-boot.pre-upgrade
            else
                cleanup_efi_files
            fi
        fi
        /opt/roche/sbin/rlx-create-efi-boot.sh
    fi
}
