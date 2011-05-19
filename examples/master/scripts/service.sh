#!/bin/sh

### BEGIN INIT INFO
# Provides:          popc-jobmgr
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Starts the POP-C++ job manager
# Description:       
### END INIT INFO
# Author: Jonathan Stoppani (jonathan.stoppani@edu.hefr.ch)

DAEMON=/usr/local/popc/sbin/SXXpopc
PIDFILE="/tmp/jobmgr.pid"

if [ ! -x $DAEMON ]; then
  echo "ERROR: Can't execute $DAEMON."
  exit 1
fi

start_service() {
  echo -n " * Starting job manager... "
  start-stop-daemon -Sq -p $PIDFILE -x $DAEMON -- start >&2
  e=$?

  if [ $e -eq 1 ]; then
    echo "already running"
    return
  elif [ $e -eq 255 ]; then
    echo "couldn't start"
    return
  else
    print_status
  fi
}

print_status() {
   if is_alive; then
      echo "[running]"
   else
      echo "[stopped]"
   fi
}

is_alive() {
	ret=1
	if [ -r $PIDFILE ] ; then
	   pid=`cat $PIDFILE`
	   if [ -e /proc/$pid ] ; then
	      procname=`/bin/ps h -p $pid -C bind`
	      [ -n "$procname" ] && ret=0
	   fi
	fi
	return $ret
}

service_status() {
	echo -n " * Getting job manager status... "
	
	if is_alive; then
		echo "running"
		return 1
	else
		echo "not running"
		return 0
	fi
}

stop_service() {
  echo -n " * Stopping job manager... "
  $DAEMON stop >&2
  e=$?
  #start-stop-daemon -Kq -R 10 -p $PIDFILE
  if [ $e -eq 1 ]; then
    echo "failed"
    return
  else
    sleep 2
    print_status
  fi
}

case "$1" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  status)
    service_status
    ;;
  force-reload|restart)
    stop_service
    start_service
    ;;
  *)
    echo "Usage: /etc/init.d/popc-jobmgr {start|stop|status|restart|force-reload}" >&2
    exit 1
    ;;
esac

exit 0