#!/bin/bash
# Enhanced Multilingual Rasa Model Training Script
# Trains language-specific models and optional unified multilingual model

set -e  # Exit on error
set -u  # Treat unset variables as error
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RASA_DIR="$PROJECT_ROOT/rasa_nlu"
MODELS_DIR="$RASA_DIR/models"
DATA_DIR="$RASA_DIR/data"
LOGS_DIR="$PROJECT_ROOT/.playbook/training_logs"
# Virtualenv path and python interpreter detection (configurable via env)
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/.venv}" # Define virtual environment path
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python)"
    else
        echo "Python no encontrado en PATH. Defina PYTHON_BIN o instale python3." >&2
        exit 1
    fi
fi
REUSE_VENV="${REUSE_VENV:-true}" # true to reuse existing venv, false to recreate

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LANGUAGES=${LANGUAGES:-"es en pt"}  # Languages to train
TRAIN_MULTILINGUAL=${TRAIN_MULTILINGUAL:-"true"}  # Whether to train unified model
RASA_CONFIG=${RASA_CONFIG:-"$RASA_DIR/config_enhanced.yml"}
DOMAIN_FILE=${DOMAIN_FILE:-"$RASA_DIR/domain_enhanced.yml"}
MIN_CONFIDENCE=${MIN_CONFIDENCE:-"0.8"}  # Minimum confidence threshold
CROSS_VALIDATION=${CROSS_VALIDATION:-"false"}  # Enable cross-validation

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ⚠️ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ❌ $1"
}
check_dependencies() {
    log "Checking dependencies..."

    # Ensure virtual environment exists (reuse if allowed)
    if [[ -d "$VENV_PATH" && "$REUSE_VENV" == "true" ]]; then
        log "Reusing existing virtual environment at $VENV_PATH"
    else
        if [[ -d "$VENV_PATH" ]]; then
            log_warning "Removing existing virtual environment at $VENV_PATH (REUSE_VENV=false)"
            rm -rf "$VENV_PATH"
        fi
        log "Creating virtual environment at $VENV_PATH using ${PYTHON_BIN}..."
        "${PYTHON_BIN}" -m venv "$VENV_PATH"
        log_success "Virtual environment created."
    fi

    # Activate virtual environment for this script's context
    # This is not strictly necessary for explicit calls like "$VENV_PATH/bin/pip"
    # but good practice for clarity if other commands were to be added.
    # source "$VENV_PATH/bin/activate" # Not needed for explicit calls

    # Check if Rasa is installed in the virtual environment
    if ! "$VENV_PATH/bin/rasa" --version &> /dev/null; then
        log_warning "Rasa CLI not found in virtual environment. Installing..."
        "$VENV_PATH/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
        "$VENV_PATH/bin/pip" install "rasa>=3.6.0"
        log_success "Rasa CLI installed in virtual environment."
    else
        log_success "Rasa CLI already installed in virtual environment."
    fi

    # Check if required files exist
    if [[ ! -f "$RASA_CONFIG" ]]; then
        log_error "Rasa config file not found: $RASA_CONFIG"
        exit 1
    fi

    if [[ ! -f "$DOMAIN_FILE" ]]; then
        log_error "Domain file not found: $DOMAIN_FILE"
        exit 1
    fi

    log_success "Dependencies check passed"
}

prepare_directories() {
    log "Preparing directories..."

    mkdir -p "$MODELS_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$DATA_DIR"

    log_success "Directories prepared"
}

validate_training_data() {
    local lang=$1
    local data_file="$DATA_DIR/nlu_${lang}.yml"

    log "Validating training data for $lang..."

    if [[ ! -f "$data_file" ]]; then
        log_error "Training data not found: $data_file"
        return 1
    fi

    # Check if file has content
    if [[ ! -s "$data_file" ]]; then
        log_error "Training data file is empty: $data_file"
        return 1
    fi

    # Count number of intents and examples
    local intent_count=$(grep -c "- intent:" "$data_file" || echo "0")
    local example_count=$(grep -c "    - " "$data_file" || echo "0")

    if [[ $intent_count -lt 3 ]]; then
        log_warning "Low number of intents ($intent_count) in $lang data"
    fi

    if [[ $example_count -lt 20 ]]; then
        log_warning "Low number of examples ($example_count) in $lang data"
    fi

    log "Training data for $lang: $intent_count intents, $example_count examples"
    return 0
}

train_language_model() {
    local lang=$1
    local model_name="nlu_enhanced_${lang}"
    local data_file="$DATA_DIR/nlu_${lang}.yml"
    local output_path="$MODELS_DIR/${model_name}.tar.gz"
    local log_file="$LOGS_DIR/training_${lang}_$(date +%Y%m%d_%H%M%S).log"

    log "Training model for language: $lang"

    # Validate data first
    if ! validate_training_data "$lang"; then
        log_error "Data validation failed for $lang"
        return 1
    fi

    # Create temporary training directory
    local temp_dir=$(mktemp -d)
    cp "$RASA_CONFIG" "$temp_dir/config.yml"
    cp "$DOMAIN_FILE" "$temp_dir/domain.yml"
    cp "$data_file" "$temp_dir/nlu.yml"

    # Train the model using the virtual environment's rasa executable
    log "Starting training for $lang (this may take several minutes)..."

    if "$VENV_PATH/bin/rasa" train nlu \
        --nlu "$temp_dir/nlu.yml" \
        --config "$temp_dir/config.yml" \
        --out "$temp_dir" \
        --fixed-model-name "$model_name" \
        --debug > "$log_file" 2>&1; then

        # Move trained model to models directory
        if [[ -f "$temp_dir/${model_name}.tar.gz" ]]; then
            mv "$temp_dir/${model_name}.tar.gz" "$output_path"
            log_success "Model trained successfully: $output_path"

            # Create symlink for latest
            ln -sf "$(basename "$output_path")" "$MODELS_DIR/latest_${lang}.tar.gz"

        else
            log_error "Training completed but model file not found"
            return 1
        fi
    else
        log_error "Training failed for $lang. Check log: $log_file"
        return 1
    fi

    # Cleanup
    rm -rf "$temp_dir"

    # Run cross-validation if enabled
    if [[ "$CROSS_VALIDATION" == "true" ]]; then
        run_cross_validation "$lang" "$data_file"
    fi

    return 0
}

main() {
    log "Starting Enhanced Multilingual Model Training"
    log "Languages: $LANGUAGES"
    log "Multilingual: $TRAIN_MULTILINGUAL"

    # Setup
    check_dependencies
    prepare_directories

    local success_count=0
    local total_models=0

    # Train language-specific models
    for lang in $LANGUAGES; do
        total_models=$((total_models + 1))
        if train_language_model "$lang"; then
            success_count=$((success_count + 1))
        fi
    done

    # Summary
    log_success "Training completed: $success_count/$total_models models successful"

    if [[ $success_count -eq $total_models ]]; then
        log_success "All models trained successfully!"
        exit 0
    else
        log_warning "Some models failed to train. Check logs in: $LOGS_DIR"
        exit 1
    fi
}

# Handle script arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --languages)
            LANGUAGES="$2"
            shift 2
            ;;
        --cross-validation)
            CROSS_VALIDATION="true"
            shift
            ;;
        --config)
            RASA_CONFIG="$2"
            shift 2
            ;;
        --domain)
            DOMAIN_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --languages LANGS     Languages to train (default: 'es en pt')"
            echo "  --cross-validation    Enable cross-validation testing"
            echo "  --config FILE         Rasa config file"
            echo "  --domain FILE         Domain file"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
