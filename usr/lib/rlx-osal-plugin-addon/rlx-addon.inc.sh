#!/bin/sh

ADDON_LOG=/opt/roche/var/log/rlx-addon.log
ADDON_HISTORY_LOG=/opt/roche/var/log/rlx-addon-history.log

log_error()
{
    echo "E: $@" >> ${ADDON_LOG}
    exit 1
}

log_warn()
{
    echo "W: $@" >> ${ADDON_LOG}
}

log_info()
{
    echo "I: $@" >> ${ADDON_LOG}
}

log_debug()
{
    echo "D: $@" >> ${ADDON_LOG}
}

log_history()
{
    echo "$@" >> ${ADDON_HISTORY_LOG}
}

exit_on_error()
{
    if [ $? -ne 0 ]; then
        log_error $@
    fi
}

restore_apt_sources()
{
    test ! -e /etc/apt/sources.list.save || mv -f /etc/apt/sources.list.save /etc/apt/sources.list
}

verify_signature_addon()
{
    WORK_DIR=$1

    file=sha256.sums
    test `passwd -S roche | cut -d ' ' -f2` = 'P'
    user_is_locked=$?  # 1 - locked, if no password (prod) or locked, 0 - not locked, if password set (dev, test)
    if [ ! -f $WORK_DIR/$file.signature ]; then  # no signature file found
        if [ $user_is_locked -eq 0 ]; then
            log_warn "Warning: accepting missing signature, roche account is not locked"
        else
            log_error "Error: no signature found in addon archive"
        fi
    else
        /opt/roche/sbin/ssl-verify.sh $WORK_DIR/$file $WORK_DIR/$file.signature
        if [ $? -ne 0 ]; then
            if [ $user_is_locked -eq 0 ]; then
                log_warn "Warning: accepting wrong signature, roche account is not locked"
            else
                log_error "Error: invalid signature in addon archive"
            fi
        fi
        rm -f $WORK_DIR/$file.signature
    fi
}

install_addon()
{
    PACKAGE_NAME=$1
    WORK_DIR=$2

    if [ -z "${PACKAGE_NAME}" ]; then
        log_error "Empty package name"
    fi

    if [ -z "${WORK_DIR}" ]; then
        log_error "Empty work directory"
    fi

    verify_signature_addon "$WORK_DIR"

    addon_type="deb"
    if [ -f ${WORK_DIR}/${PACKAGE_NAME}/.addon_type ]; then
        addon_type=`cat ${WORK_DIR}/${PACKAGE_NAME}/.addon_type`
    fi

    log_info "Installing $PACKAGE_NAME"
    case "$addon_type" in
        deb)
            install_addon_deb_packages "$PACKAGE_NAME" "$WORK_DIR"
            exit_on_error "Error installing $PACKAGE_NAME"
        ;;
        docker)
            install_addon_deb_packages "$PACKAGE_NAME" "$WORK_DIR"
            exit_on_error "Error installing $PACKAGE_NAME [deb]"
            install_addon_docker_containers "$PACKAGE_NAME" "$WORK_DIR"
            exit_on_error "Error installing $PACKAGE_NAME [docker]"
        ;;
        helm)
            install_addon_deb_packages "$PACKAGE_NAME" "$WORK_DIR"
            exit_on_error "Error installing $PACKAGE_NAME [deb]"
            install_addon_helm_charts "$PACKAGE_NAME" "$WORK_DIR"
            exit_on_error "Error installing $PACKAGE_NAME [helm chart]"
        ;;
        *)
            log_error "Addon type unknown"
        ;;
    esac

    return 0;
}

install_addon_deb_packages()
{
    PACKAGE_NAME=$1
    WORK_DIR=$2

    # move main source list
    test ! -e /etc/apt/sources.list || mv -f /etc/apt/sources.list /etc/apt/sources.list.save

    # copy the new temporary source list
    if ! sed "s#@REPO_PATH@#$WORK_DIR#g" $WORK_DIR/debian/apt_sources_*.list > /etc/apt/sources.list ; then
        restore_apt_sources
        log_error "No apt source list found in the addon archive"
    fi

    export DEBIAN_FRONTEND=noninteractive
    # Ignore sources.list.d/* files
    apt-get -qy update -o Dir::Etc::SourceParts=/non-existing-dir
    if [ $? -ne 0 ]; then
        restore_apt_sources
        log_error "Error updating apt sources"
    fi

    package_version=`find $WORK_DIR/debian/pool/ -name ${PACKAGE_NAME}_*_*.deb 2>/dev/null | xargs basename | cut -d_ -f2`
    apt-get install -qy --allow-downgrades $PACKAGE_NAME=$package_version >> $ADDON_LOG 2>&1
    retval=$?

    # Restore original sources.list
    restore_apt_sources

    return $retval
}

addon_find_docker_compose_files_in_package()
{
    dpkg -L $1 | grep "docker-compose*\.ya\?ml"
}

install_addon_docker_containers()
{
    PACKAGE_NAME=$1
    WORK_DIR=$2

    DOCKER_CONTAINERS="${WORK_DIR}/${PACKAGE_NAME}/docker-containers.tar"
    if [ ! -e "$DOCKER_CONTAINERS" ]; then
        log_debug "no docker containers found for $PACKAGE_NAME"
        return
    fi

    log_info "Loading docker containers for $PACKAGE_NAME"
    docker load -i "$DOCKER_CONTAINERS"
    exit_on_error "Error loading docker containers tarball $DOCKER_CONTAINERS"
    unset DOCKER_CONTAINERS

    docker_compose_files=$(addon_find_docker_compose_files_in_package $PACKAGE_NAME)
    for fname in $docker_compose_files; do
        log_info "Processing docker-compose file $fname"
        docker-compose --no-ansi -f $fname up --no-start
        exit_on_error "Error processing docker-compose file $fname"
    done
    unset docker_compose_files
}

addon_find_service_configuration_files_in_package()
{
    dpkg -L $1 | grep "service_configuration.yml"
}

#helm_chart_test()
#{
#    tar ft $1 | grep -qE Chart.ya?ml$
#    return $?
#}

#addon_find_helm_charts_in_package()
#{
#    helm_chart_files_candidates=`dpkg -L $1 | grep ^.*\.tgz$`
#    helm_chart_files=""
#    for f in $helm_chart_files_candidates; do
#        if helm_chart_test $f; then
#            helm_chart_files="$helm_chart_files $f"
#        fi
#    done
#    if [ -z "$helm_chart_files" ]; then
#        log_error "No helm chart files found in $1"
#    fi
#    echo "$helm_chart_files"
#}

addon_find_hookpath_in_service_configuration_dir()
{
    hookfile=`find $1 -name *inst.sh | tail -n1`
    if [ -n "$hookfile" ]; then
        echo -n `echo "$hookfile" | xargs dirname`
    else
        echo -n ""
    fi
}

install_addon_helm_charts()
{
    PACKAGE_NAME=$1
    WORK_DIR=$2

    DOCKER_CONTAINERS="${WORK_DIR}/${PACKAGE_NAME}/docker-containers.tar"
    if [ ! -e "$DOCKER_CONTAINERS" ]; then
        log_debug "no docker containers found for $PACKAGE_NAME"
    else
        log_info "Loading docker containers for $PACKAGE_NAME"
        docker load -i "$DOCKER_CONTAINERS"
        exit_on_error "Error loading docker containers tarball $DOCKER_CONTAINERS"
    fi
    unset DOCKER_CONTAINERS

    service_configuration_files=$(addon_find_service_configuration_files_in_package $PACKAGE_NAME)
    if [ -z "$service_configuration_files" ]; then
        log_error "No service configuration files found in $1"
    fi

    for fname in $service_configuration_files; do
        log_info "Installing helm chart from $fname"
        service_configuration_dir=`echo $fname | xargs dirname`
        hookpath=$(addon_find_hookpath_in_service_configuration_dir $service_configuration_dir)
        log_debug "hookpath: '$hookpath'"
        if [ -z "$hookpath" ]; then
            log_debug "Installing helm chart without hooks"
            log_debug "Running /opt/roche/sbin/rlx-addon-install-helm-chart $fname $WORK_DIR/$PACKAGE_NAME"
            /opt/roche/sbin/rlx-addon-install-helm-chart $fname "$WORK_DIR/$PACKAGE_NAME"
            exit_on_error "Error installing helm chart from $fname"
        else
            log_debug "Installing helm chart with hooks"
            log_debug "Running /opt/roche/sbin/rlx-addon-install-helm-chart $fname $WORK_DIR/$PACKAGE_NAME $hookpath"
            /opt/roche/sbin/rlx-addon-install-helm-chart $fname "$WORK_DIR/$PACKAGE_NAME" $hookpath
            exit_on_error "Error installing helm chart from $fname"
        fi
        unset service_configuration_dir
        unset hookpath
    done
    unset service_configuration_files
}

remove_addon()
{
    PACKAGE_NAME=$1

    if [ -z "${PACKAGE_NAME}" ]; then
        log_error "Empty package name"
    fi

    log_info "Removing $PACKAGE_NAME"
    # Note: first remove helm charts and docker containers because we need to inspect the
    # package to find out which docker-files to process

    remove_addon_helm_charts $PACKAGE_NAME
    exit_on_error "Error removing $PACKAGE_NAME"

    remove_addon_docker_containers $PACKAGE_NAME
    exit_on_error "Error removing $PACKAGE_NAME"

    remove_addon_deb_packages $PACKAGE_NAME
    exit_on_error "Error removing $PACKAGE_NAME"

    return 0
}

remove_addon_deb_packages()
{
    PACKAGE_NAME=$1
    apt-get autoremove --purge -qy "${PACKAGE_NAME}" >> ${ADDON_LOG} 2>&1
    retval=$?
    if [ $retval -ne 0 ]; then
        log_warn "Error removing ${PACKAGE_NAME}: $retval"
    fi
    return $retval
}

remove_addon_docker_containers()
{
    PACKAGE_NAME=$1
    docker_compose_files=$(addon_find_docker_compose_files_in_package $PACKAGE_NAME)
    for fname in $docker_compose_files; do
        log_info "Processing docker-compose file $fname"
        docker-compose --no-ansi -f $fname down --rmi all --volumes --remove-orphans --timeout 60
        exit_on_error "Error removing docker containers in $fname"
    done
    unset docker_compose_files
    return 0
}


wait_until_pods_terminated()
{
    timeout=$1
    pods="$2"
    namespace=$3
    err="$4"
    t=0
    while kubectl get pods -n $namespace 2>/dev/null | grep -q ^$pods-; do
        sleep 1
        t=$((t+1))
        if [ $t -gt $timeout ]; then
            log_warn "$err"
        fi
    done
}

remove_addon_helm_charts()
{
    PACKAGE_NAME=$1
    service_configuration_files=$(addon_find_service_configuration_files_in_package $PACKAGE_NAME)
    export KUBECONFIG=/opt/roche/home/.kube/config
    for fname in $service_configuration_files; do
        log_info "Processing service configuration file $fname"

        for s in `cat $fname | grep ^"[a-zA-Z0-9].*"`; do

            section=`sed -n "/^$s/,/^[^ ]/p" $fname | sed '$ { /^[a-zA-Z0-9]/d; }'`

            servicename=`echo "$section" | grep "servicename:" | awk {'print $NF'}`
            imagename=`echo "$section" | grep "imagename:" | awk {'print $NF'}`
            namespace=`echo "$section" | grep "namespace:" | awk {'print $NF'}`
            helm uninstall --wait $servicename -n $namespace

            # remove cron jobs
            crons=`kubectl get po -n $namespace | grep ^$servicename-cron | awk {'print $1'}`
            for cron in $crons; do
                kubectl delete po $cron -n $namespace
            done
            # remove hooks
            hooks=`kubectl get po -n $namespace | grep ^$servicename-hook | awk {'print $1'}`
            for hook in $hooks; do
                kubectl delete po $hook -n $namespace
            done
            unset crons
            unset hooks

            # it does not wait until pods are terminated https://github.com/helm/helm/issues/10586
            wait_until_pods_terminated 120 $servicename $namespace "Timeout terminating pods for $servicename"
            wait_until_pods_terminated 120 $imagename $namespace "Timeout terminating pods for $servicename"
            unset servicename
            unset imagename
            unset namespace

            docker_image_registry=`echo "$section" | grep "imageregistry:" | awk '{print $NF}'`
            docker_image_name=`echo "$section" | grep "imagename:" | awk '{print $NF}'`
            docker_image_tag=`echo "$section" | grep "imagetag:" | awk '{print $NF}'`
            # handle case when null values are set
            if [ "$docker_image_registry" = "null" ]; then
                docker_image_registry=""
            fi
            if [ "$docker_image_name" = "null" ]; then
                docker_image_name=""
            fi
            if [ "$docker_image_tag" = "null" ]; then
                docker_image_tag=""
            fi
            if [ -n "$docker_image_registry" -a -n "$docker_image_name" -a -n "$docker_image_tag" ]; then
                docker_image="$docker_image_registry/$docker_image_name:$docker_image_tag"
                # do not force as it might be used by  other containers
                docker image rm $docker_image || true
            fi
            unset docker_image_registry
            unset docker_image_name
            unset docker_image_tag
        done
    done
    unset service_configuration_files
    return 0
}
