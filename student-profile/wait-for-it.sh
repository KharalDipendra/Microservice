#!/usr/bin/env bash
# wait-for-it.sh - wait until a TCP host:port is ready
#
# Purpose:
#   A  helper script used in Docker images to slow down starting the application
#   until a dependent service (usually a database) is ready to be accepting TCP connections.
#   In our microservice architecture we use it to wait for the Postgres container
#   (service name: student-db) to be installed, up and ready before launching the Flask app. 
#   Otherwise the Flask app will start before Postgres is ready, and then error saying no database is working.
#
# Usage examples:
#   ./wait-for-it.sh student-db 5432 -- echo "db ready"
#   ./wait-for-it.sh student-db 5432 python app.py
#
# Notes:
# - This script relies on `nc` (netcat) being installed inside the container.
#   On Debian/Ubuntu images the package may be called netcat-traditional or
#   netcat-openbsd. On Alpine you can use `apk add --no-cache netcat-openbsd`.
# - We use exec "$@" at the end so the command we run inherits the PID (good
#   for signal handling inside containers).

host="$1"            # first argument: hostname (e.g. student-db)
port="$2"            # second argument: port number (e.g. 5432)
shift 2              # remove the first two args so "$@" becomes the command to run

echo "Waiting for $host:$port..."

# The loop:
# - `nc -z "$host" "$port"` attempts to open a TCP connection to host:port
#   with zero-I/O mode (-z). It returns 0 when the port is open, non-zero otherwise.
# - `while ! nc -z ...; do sleep 1; done` repeats the test every 1 second.
# - The exclamation mark (!) negates the result so the loop continues while
#   the port is NOT open.
while ! nc -z "$host" "$port"; do
  # Sleep a short time before trying again to avoid busy-waiting.
  sleep 1
done

# At this point the port is reachable (nc returned success)
echo "$host:$port is available. Executing command..."

# exec replaces the current shell process with the command and its arguments.
# This is important in Docker because:
#  - it ensures the child process receives signals (SIGTERM) directly
#  - there is no extra shell process left behind, so container shutdown
#    and signal handling behave as expected.
exec "$@"

### Important Note ###
# This simple approach has no timeout — in production you should add a timeout 
# to avoid infinite waiting if the dependency never comes up. Example lightweight 
# timeout idea (for advanced students) is shown below.
#
# start_time=$SECONDS
# timeout=60  # seconds
# while ! nc -z "$host" "$port"; do
#   if (( SECONDS - start_time >= timeout )); then
#     echo "Timeout waiting for $host:$port" >&2
#     exit 1
#   fi
#   sleep 1
# done
# echo "$host:$port is available. Executing command..."
# exec "$@"