#!/bin/bash

DOCKER_DIR=$(readlink -f $(dirname "$0"))
source "${DOCKER_DIR}/../logging.sh"
WPTDASHBOARD_DIR=${WPTDASHBOARD_DIR:-$(readlink -f "${DOCKER_DIR}/../..")}

# Execute code in docker instance:
#
# -u $(id -u $USER):$(id -g $USER)  Run as current user and group
# wptdashboard-instance             Name of instance (wptdashboard dev server)

EXEC_STR=""
for ARG in "${@}"; do
  EXEC_STR+="\"${ARG}\" "
done
info "Execute-in-docker:  ${EXEC_STR}"
docker exec -u $(id -u $USER):$(id -g $USER) wptd-dev-instance "${@}"
DOCKER_STATUS=${?}
if [ "${DOCKER_STATUS}" != "0" ]; then
  error "Execute-in-docker failed. Is docker instance 'wptdashboard-instance' running?"
else
  info "Execute-in-docker complete."
fi
exit ${DOCKER_STATUS}