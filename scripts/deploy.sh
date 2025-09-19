#!/bin/bash

# CashMate Deployment Script
# This script helps deploy CashMate to various environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="cashmate"
DOCKER_IMAGE="cashmate:latest"
DOCKER_CONTAINER="cashmate-bot"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_error ".env file not found. Please create it from .env.example"
        exit 1
    fi

    log_success "Dependencies check passed"
}

build_image() {
    log_info "Building Docker image..."

    if [ "$1" = "--no-cache" ]; then
        docker build --no-cache -t $DOCKER_IMAGE .
    else
        docker build -t $DOCKER_IMAGE .
    fi

    if [ $? -eq 0 ]; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

deploy_local() {
    log_info "Deploying to local environment..."

    # Stop existing container if running
    if docker ps -q -f name=$DOCKER_CONTAINER | grep -q .; then
        log_warning "Stopping existing container..."
        docker stop $DOCKER_CONTAINER
    fi

    # Remove existing container
    if docker ps -a -q -f name=$DOCKER_CONTAINER | grep -q .; then
        log_warning "Removing existing container..."
        docker rm $DOCKER_CONTAINER
    fi

    # Run new container
    log_info "Starting new container..."
    docker run -d \
        --name $DOCKER_CONTAINER \
        --env-file .env \
        --restart unless-stopped \
        $DOCKER_IMAGE

    if [ $? -eq 0 ]; then
        log_success "Container deployed successfully"
        log_info "Container ID: $(docker ps -q -f name=$DOCKER_CONTAINER)"
        log_info "Use 'docker logs -f $DOCKER_CONTAINER' to view logs"
    else
        log_error "Failed to deploy container"
        exit 1
    fi
}

deploy_production() {
    log_info "Deploying to production environment..."

    # Build optimized image
    build_image --no-cache

    # Stop existing container
    if docker ps -q -f name=$DOCKER_CONTAINER | grep -q .; then
        log_info "Stopping existing container..."
        docker stop $DOCKER_CONTAINER || true
    fi

    # Remove existing container
    if docker ps -a -q -f name=$DOCKER_CONTAINER | grep -q .; then
        log_info "Removing existing container..."
        docker rm $DOCKER_CONTAINER || true
    fi

    # Run production container
    log_info "Starting production container..."
    docker run -d \
        --name $DOCKER_CONTAINER \
        --env-file .env \
        --restart unless-stopped \
        --log-driver json-file \
        --log-opt max-size=10m \
        --log-opt max-file=3 \
        $DOCKER_IMAGE

    if [ $? -eq 0 ]; then
        log_success "Production deployment successful"
        log_info "Container ID: $(docker ps -q -f name=$DOCKER_CONTAINER)"
    else
        log_error "Production deployment failed"
        exit 1
    fi
}

show_status() {
    log_info "Checking deployment status..."

    if docker ps -q -f name=$DOCKER_CONTAINER | grep -q .; then
        log_success "Container is running"
        docker ps -f name=$DOCKER_CONTAINER

        log_info "Recent logs:"
        docker logs --tail 10 $DOCKER_CONTAINER
    else
        log_warning "Container is not running"

        if docker ps -a -q -f name=$DOCKER_CONTAINER | grep -q .; then
            log_info "Container exists but is stopped"
            docker ps -a -f name=$DOCKER_CONTAINER
        else
            log_info "Container does not exist"
        fi
    fi
}

show_logs() {
    if docker ps -q -f name=$DOCKER_CONTAINER | grep -q .; then
        log_info "Showing container logs..."
        docker logs -f $DOCKER_CONTAINER
    else
        log_error "Container is not running"
        exit 1
    fi
}

stop_deployment() {
    log_info "Stopping deployment..."

    if docker ps -q -f name=$DOCKER_CONTAINER | grep -q .; then
        docker stop $DOCKER_CONTAINER
        log_success "Container stopped"
    else
        log_warning "Container is not running"
    fi
}

cleanup() {
    log_info "Cleaning up old images and containers..."

    # Remove stopped containers
    docker container prune -f

    # Remove dangling images
    docker image prune -f

    # Remove unused images (older than 24 hours)
    docker image prune -a --filter "until=24h" -f

    log_success "Cleanup completed"
}

show_help() {
    echo "CashMate Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       Build Docker image"
    echo "  deploy      Deploy to local environment"
    echo "  production  Deploy to production environment"
    echo "  status      Show deployment status"
    echo "  logs        Show container logs"
    echo "  stop        Stop deployment"
    echo "  cleanup     Clean up old images and containers"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 deploy"
    echo "  $0 production"
    echo "  $0 status"
    echo "  $0 logs"
}

# Main script
case "${1:-help}" in
    build)
        check_dependencies
        build_image
        ;;
    deploy)
        check_dependencies
        build_image
        deploy_local
        ;;
    production)
        check_dependencies
        deploy_production
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    stop)
        stop_deployment
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac