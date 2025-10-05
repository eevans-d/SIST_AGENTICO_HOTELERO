# Phase E.3 - Rasa NLP Training & Integration

## 🎯 Objective
Implement production-ready Rasa NLP with DIET classifier for intent recognition and entity extraction, replacing mock NLP with real Machine Learning model.

## 📋 Current State Analysis

### Existing Implementation (Mock)
```python
# nlp_engine.py - Line 66-69
async def _process_with_retry(self, text: str) -> dict:
    # Mock response hasta que se entrene y cargue un modelo Rasa
    return {"intent": {"name": "check_availability", "confidence": 0.95}, "entities": []}
```

**Problems**:
- ❌ Always returns same intent (check_availability)
- ❌ No entity extraction (dates, numbers, names ignored)
- ❌ Fake confidence (always 0.95)
- ❌ No learning or improvement
- ❌ Cannot handle 15+ different intents needed for production

### Training Data Status
- **Current**: 2 intents, ~30 examples
- **Target**: 15+ intents, 200+ examples

## 🔧 Tasks Breakdown

### Task 1: Expand Training Data (90 min)
**File**: `rasa_nlu/data/nlu.yml`

**New Intents to Add** (15 total):
1. ✅ check_availability (expand 15→50 examples)
2. ✅ make_reservation (expand 15→50 examples)
3. ❌ cancel_reservation (NEW - 30 examples)
4. ❌ modify_reservation (NEW - 30 examples)
5. ❌ ask_price (NEW - 25 examples)
6. ❌ ask_amenities (NEW - 25 examples)
7. ❌ ask_location (NEW - 20 examples)
8. ❌ ask_policies (NEW - 20 examples)
9. ❌ ask_room_types (NEW - 20 examples)
10. ❌ greeting (NEW - 15 examples)
11. ❌ goodbye (NEW - 15 examples)
12. ❌ affirm (NEW - 15 examples)
13. ❌ deny (NEW - 15 examples)
14. ❌ help (NEW - 15 examples)
15. ❌ out_of_scope (NEW - 20 examples)

**Entity Types**:
- dates (check_in, check_out)
- numbers (guests, nights, room_number)
- room_type (standard, deluxe, suite)
- amenity (wifi, pool, gym, parking)
- price_range (budget, medium, luxury)

### Task 2: Configure DIET Classifier (30 min)
**File**: `rasa_nlu/config.yml`

**Pipeline Components**:
```yaml
language: es
pipeline:
  - name: WhitespaceTokenizer
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
  - name: CountVectorsFeaturizer
    analyzer: char_wb
    min_ngram: 1
    max_ngram: 4
  - name: DIETClassifier
    epochs: 100
    constrain_similarities: true
    model_confidence: softmax
  - name: EntitySynonymMapper
  - name: ResponseSelector
    epochs: 100
```

### Task 3: Create Training Script (20 min)
**File**: `scripts/train_rasa.sh` (NEW)

**Features**:
- Train NLU model
- Validate training data
- Generate model .tar.gz
- Cross-validation
- Performance report

### Task 4: Update NLP Engine (45 min)
**File**: `app/services/nlp_engine.py`

**Changes**:
- Remove mock implementation
- Load Rasa Agent from model
- Add model versioning
- Cache model in memory
- Fallback to rule-based if model unavailable
- Entity extraction and normalization

### Task 5: Create Entity Extractors (30 min)
**File**: `app/services/entity_extractors.py` (NEW)

**Extractors**:
- DateExtractor (duckling/dateparser)
- NumberExtractor (guests, nights)
- RoomTypeExtractor (synonym mapping)
- AmenityExtractor (fuzzy matching)

### Task 6: Integration Tests (45 min)
**File**: `tests/integration/test_nlp_integration.py` (NEW)

**Test Coverage** (30+ tests):
- Intent classification accuracy
- Entity extraction correctness
- Confidence calibration
- Fallback behavior
- Multi-language support (es)
- Edge cases (typos, ambiguity)

### Task 7: Benchmark Performance (30 min)
**File**: `scripts/benchmark_nlp.py` (NEW)

**Metrics**:
- Precision per intent (>85%)
- Recall per intent (>80%)
- F1-Score overall (>82%)
- Confusion matrix
- Entity extraction accuracy

### Task 8: Documentation (30 min)
**File**: `PROJECT_GUIDE.md`

**Topics**:
- Training process
- Model versioning
- Intent list with examples
- Entity types
- Confidence thresholds
- Retraining procedure

## 📊 Success Criteria

✅ **Training Data**:
- [ ] 15+ intents defined
- [ ] 200+ training examples
- [ ] 5+ entity types
- [ ] Balanced distribution

✅ **Model Performance**:
- [ ] Intent accuracy >85%
- [ ] Entity extraction >80%
- [ ] Confidence calibration <0.1 deviation
- [ ] Training time <5 minutes

✅ **Integration**:
- [ ] Model loads successfully
- [ ] Fallback works if model unavailable
- [ ] Entity normalization working
- [ ] No type errors

✅ **Testing**:
- [ ] 30+ integration tests passing
- [ ] Benchmark report generated
- [ ] Cross-validation >80%

✅ **Documentation**:
- [ ] Training guide complete
- [ ] Intent catalog documented
- [ ] Retraining procedure defined

## 📈 Expected Impact

### Metrics Before E.3:
- Quality Score: 9.7/10
- NLP Accuracy: 0% (mock)
- Intents: 1 (fake)
- Entity Extraction: NO
- Automation Rate: ~30%

### Metrics After E.3:
- Quality Score: **9.8/10** ⬆️ (+0.1)
- NLP Accuracy: **85%+** ⬆️ (+∞)
- Intents: **15+** ⬆️ (+1400%)
- Entity Extraction: **YES** ⬆️ (5+ types)
- Automation Rate: **85%+** ⬆️ (+183%)

## ⏱️ Timeline

| Task | Duration | Status |
|------|----------|--------|
| 1. Training Data | 90 min | 🔜 NEXT |
| 2. DIET Config | 30 min | ⏳ PENDING |
| 3. Training Script | 20 min | ⏳ PENDING |
| 4. Update NLP Engine | 45 min | ⏳ PENDING |
| 5. Entity Extractors | 30 min | ⏳ PENDING |
| 6. Integration Tests | 45 min | ⏳ PENDING |
| 7. Benchmark | 30 min | ⏳ PENDING |
| 8. Documentation | 30 min | ⏳ PENDING |
| **TOTAL** | **5h 20min** | **0%** |

## 🚀 Execution Start

Date: October 5, 2025 05:00 UTC
Priority: HIGH (Production Critical)
Next Action: Task 1 - Expand Training Data
Target: Real ML-based NLP (not mock)
