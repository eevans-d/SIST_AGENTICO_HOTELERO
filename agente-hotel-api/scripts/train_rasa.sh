#!/usr/bin/env bash
# [PROMPT 2.5 + E.3] scripts/train_rasa.sh
# Rasa NLU Training Script with validation and performance reporting

set -euo pipefail

# ==================== CONFIGURATION ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RASA_DIR="$PROJECT_ROOT/rasa_nlu"
MODEL_DIR="$RASA_DIR/models"
RESULTS_DIR="$PROJECT_ROOT/.playbook/rasa_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==================== LOGGING ====================
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

# ==================== VALIDATION ====================
validate_environment() {
    log_info "Validating environment..."
    
    # Check Python version
    if ! command -v python &> /dev/null; then
        log_error "Python not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check Rasa installation
    if ! python -c "import rasa" &> /dev/null; then
        log_error "Rasa not installed. Run: pip install rasa"
        exit 1
    fi
    
    local RASA_VERSION=$(python -c "import rasa; print(rasa.__version__)" 2>/dev/null || echo "unknown")
    log_success "Rasa version: $RASA_VERSION"
}

validate_training_data() {
    log_info "Validating training data..."
    
    if [ ! -f "$RASA_DIR/data/nlu.yml" ]; then
        log_error "Training data not found: $RASA_DIR/data/nlu.yml"
        exit 1
    fi
    
    if [ ! -f "$RASA_DIR/config.yml" ]; then
        log_error "Config not found: $RASA_DIR/config.yml"
        exit 1
    fi
    
    if [ ! -f "$RASA_DIR/domain.yml" ]; then
        log_error "Domain not found: $RASA_DIR/domain.yml"
        exit 1
    fi
    
    # Validate with Rasa
    log_info "Running Rasa data validation..."
    cd "$RASA_DIR"
    if rasa data validate --domain domain.yml --data data; then
        log_success "Training data is valid"
    else
        log_error "Training data validation failed"
        exit 1
    fi
}

# ==================== TRAINING ====================
train_model() {
    log_info "Starting Rasa NLU training..."
    
    # Create model directory
    mkdir -p "$MODEL_DIR"
    mkdir -p "$RESULTS_DIR"
    
    cd "$RASA_DIR"
    
    # Train with detailed output
    log_info "Training with 100 epochs (this may take 5-10 minutes)..."
    
    if rasa train nlu \
        --config config.yml \
        --nlu data/nlu.yml \
        --domain domain.yml \
        --out "$MODEL_DIR" \
        --fixed-model-name "hotel_nlu_${TIMESTAMP}" \
        2>&1 | tee "$RESULTS_DIR/training_${TIMESTAMP}.log"; then
        
        log_success "Model training completed"
        
        # Find the latest model
        LATEST_MODEL=$(ls -t "$MODEL_DIR"/*.tar.gz 2>/dev/null | head -n 1)
        if [ -z "$LATEST_MODEL" ]; then
            log_error "No model file found after training"
            exit 1
        fi
        
        log_success "Model saved: $LATEST_MODEL"
        
        # Create symlink to latest
        ln -sf "$(basename "$LATEST_MODEL")" "$MODEL_DIR/latest.tar.gz"
        log_info "Symlink created: $MODEL_DIR/latest.tar.gz"
        
    else
        log_error "Model training failed"
        exit 1
    fi
}

# ==================== CROSS-VALIDATION ====================
cross_validate() {
    log_info "Running cross-validation (5-fold)..."
    
    cd "$RASA_DIR"
    
    if rasa test nlu \
        --config config.yml \
        --nlu data/nlu.yml \
        --cross-validation \
        --runs 1 \
        --folds 5 \
        --out "$RESULTS_DIR/cv_${TIMESTAMP}" \
        2>&1 | tee "$RESULTS_DIR/cv_${TIMESTAMP}.log"; then
        
        log_success "Cross-validation completed"
        
        # Extract key metrics
        if [ -f "$RESULTS_DIR/cv_${TIMESTAMP}/intent_report.json" ]; then
            log_info "Generating performance report..."
            python "$SCRIPT_DIR/parse_rasa_results.py" \
                "$RESULTS_DIR/cv_${TIMESTAMP}/intent_report.json" \
                > "$RESULTS_DIR/performance_${TIMESTAMP}.txt" || true
        fi
        
    else
        log_warning "Cross-validation failed (non-critical)"
    fi
}

# ==================== PERFORMANCE REPORT ====================
generate_report() {
    log_info "Generating training report..."
    
    cat > "$RESULTS_DIR/report_${TIMESTAMP}.md" <<EOF
# Rasa NLU Training Report

**Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Model**: hotel_nlu_${TIMESTAMP}

## Training Configuration
- **Language**: Spanish (es)
- **Pipeline**: DIET Classifier
- **Epochs**: 100
- **Intents**: 15+
- **Training Examples**: 250+

## Files
- Training log: \`training_${TIMESTAMP}.log\`
- CV results: \`cv_${TIMESTAMP}/\`
- Model: \`models/hotel_nlu_${TIMESTAMP}.tar.gz\`

## Model Size
$(du -h "$MODEL_DIR/hotel_nlu_${TIMESTAMP}.tar.gz" 2>/dev/null || echo "N/A")

## Next Steps
1. Review cross-validation results in \`cv_${TIMESTAMP}/intent_report.json\`
2. Update NLP engine to load: \`models/latest.tar.gz\`
3. Run integration tests: \`pytest tests/integration/test_nlp_integration.py\`
4. Deploy to staging environment

## Usage
\`\`\`python
from rasa.core.agent import Agent

agent = Agent.load("$MODEL_DIR/latest.tar.gz")
result = await agent.parse_message("¿Hay disponibilidad para mañana?")
print(result)
\`\`\`

EOF

    log_success "Report generated: $RESULTS_DIR/report_${TIMESTAMP}.md"
}

# ==================== MAIN ====================
main() {
    echo ""
    echo "=========================================="
    echo "  Rasa NLU Training Script"
    echo "=========================================="
    echo ""
    
    validate_environment
    validate_training_data
    train_model
    cross_validate
    generate_report
    
    echo ""
    log_success "Training pipeline completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Review report: $RESULTS_DIR/report_${TIMESTAMP}.md"
    echo "  2. Check model: $MODEL_DIR/latest.tar.gz"
    echo "  3. Update NLP engine to use new model"
    echo ""
}

# Execute main
main "$@"
