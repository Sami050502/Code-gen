#!/usr/bin/env bash
#
# Port forward services required for Ponos integration testing
# Compatible with bash 3.2+ (macOS default)
#
# Services:
# - oasis: 7374:80
# - schemaregistry: 8889:80
# - pycamel: 8887:80
#
# Usage:
#   ./port_forward.sh start     # Start all port forwards in background
#   ./port_forward.sh stop      # Stop all port forwards
#   ./port_forward.sh status    # Check status of port forwards
#

PID_DIR="/tmp/dataset-builder-portforward"

# Service list (name:namespace:local_port:remote_port)
SERVICES="oasis:oasis:7374:80 schemaregistry:schemaregistry:8889:80 pycamel:pycamel:8887:80"

start_port_forward() {
    local service="$1"
    local namespace="$2"
    local local_port="$3"
    local remote_port="$4"

    echo "Starting port-forward for $service..."
    echo "  kubectl -n $namespace port-forward service/$service $local_port:$remote_port"

    # Create PID directory if needed
    mkdir -p "$PID_DIR"

    # Check if already running
    if [[ -f "$PID_DIR/$service.pid" ]]; then
        pid=$(cat "$PID_DIR/$service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Already running (PID: $pid)"
            return 0
        fi
    fi

    # Start port-forward in background
    kubectl -n "$namespace" port-forward "service/$service" "$local_port:$remote_port" &>/dev/null &
    local pid=$!

    # Save PID
    echo "$pid" > "$PID_DIR/$service.pid"
    echo "  Started (PID: $pid)"

    # Wait a moment and verify it's running
    sleep 1
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "  Warning: Port-forward may have failed to start"
        rm -f "$PID_DIR/$service.pid"
        return 1
    fi
}

stop_port_forward() {
    local service="$1"

    if [[ -f "$PID_DIR/$service.pid" ]]; then
        pid=$(cat "$PID_DIR/$service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $service (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_DIR/$service.pid"
    else
        echo "$service: not running"
    fi
}

check_status() {
    local service="$1"
    local local_port="$2"

    if [[ -f "$PID_DIR/$service.pid" ]]; then
        pid=$(cat "$PID_DIR/$service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  $service: running (PID: $pid, port: $local_port)"
            return 0
        fi
    fi
    echo "  $service: not running"
    return 1
}

case "${1:-help}" in
    start)
        echo "=== Starting Port Forwards ==="
        echo ""

        # Check kubectl context
        if ! kubectl config current-context &>/dev/null; then
            echo "Error: No kubectl context configured"
            echo "Run: aws eks --region us-east-1 update-kubeconfig --name dev-cluster-2 --alias dev-cluster-2"
            exit 1
        fi

        context=$(kubectl config current-context)
        echo "Using kubectl context: $context"
        echo ""

        for entry in $SERVICES; do
            IFS=':' read -r service namespace local_port remote_port <<< "$entry"
            start_port_forward "$service" "$namespace" "$local_port" "$remote_port"
        done

        echo ""
        echo "=== Port Forwards Started ==="
        echo ""
        echo "You can now run Ponos tests with services:"
        echo "  make int-test ARGS='--jobpaths=<job>.yaml --pycamelendpoint=localhost:8887 --registryendpoint=localhost:8889 --oasisendpoint=localhost:7374 --runcamelasactivity=true'"
        ;;

    stop)
        echo "=== Stopping Port Forwards ==="
        echo ""

        for entry in $SERVICES; do
            IFS=':' read -r service namespace local_port remote_port <<< "$entry"
            stop_port_forward "$service"
        done

        rm -rf "$PID_DIR" 2>/dev/null || true
        echo ""
        echo "All port forwards stopped"
        ;;

    status)
        echo "=== Port Forward Status ==="
        echo ""

        running=0
        total=0
        for entry in $SERVICES; do
            IFS=':' read -r service namespace local_port remote_port <<< "$entry"
            ((total++)) || true
            if check_status "$service" "$local_port"; then
                ((running++)) || true
            fi
        done

        echo ""
        echo "$running/$total services running"
        ;;

    help|*)
        echo "Usage: $0 {start|stop|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all port forwards in background"
        echo "  stop    - Stop all port forwards"
        echo "  status  - Check status of port forwards"
        echo ""
        echo "Services:"
        for entry in $SERVICES; do
            IFS=':' read -r service namespace local_port remote_port <<< "$entry"
            echo "  $service: localhost:$local_port -> $namespace/$service:$remote_port"
        done
        ;;
esac
