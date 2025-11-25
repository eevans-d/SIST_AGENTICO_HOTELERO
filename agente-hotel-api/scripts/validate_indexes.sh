#!/bin/bash
# ===================================================================
# Script: validate_indexes.sh
# Purpose: Analyze PostgreSQL indexes and provide optimization recommendations
# Author: AI Agent
# Date: 2025-10-14
# ===================================================================
# Usage: ./scripts/validate_indexes.sh [options]
# Options:
#   --host HOST         PostgreSQL host (default: localhost)
#   --port PORT         PostgreSQL port (default: 5432)
#   --user USER         PostgreSQL user (default: agente_user)
#   --password PASS     PostgreSQL password (default: from .env)
#   --database DB       Database name (default: agente_hotel)
#   --output FILE       Output JSON file (default: .playbook/index_analysis.json)
#   --help              Show this help message
# ===================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-agente_user}"
PASSWORD="${POSTGRES_PASSWORD:-}"
DATABASE="${POSTGRES_DB:-agente_hotel}"
OUTPUT_FILE=".playbook/index_analysis.json"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --password)
            PASSWORD="$2"
            shift 2
            ;;
        --database)
            DATABASE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            exit 1
            ;;
    esac
done

# Load password from .env if not provided
if [ -z "$PASSWORD" ] && [ -f ".env" ]; then
    PASSWORD=$(grep "^POSTGRES_PASSWORD=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
fi

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql command not found. Please install PostgreSQL client.${NC}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Temporary files for SQL results
TEMP_DIR=$(mktemp -d)
EXISTING_INDEXES="$TEMP_DIR/existing_indexes.txt"
UNUSED_INDEXES="$TEMP_DIR/unused_indexes.txt"
TABLE_STATS="$TEMP_DIR/table_stats.txt"
MISSING_INDEXES="$TEMP_DIR/missing_indexes.txt"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PostgreSQL Index Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Database: $DATABASE"
echo "  User: $USER"
echo ""

# Set PGPASSWORD for psql
export PGPASSWORD="$PASSWORD"

# Function to execute SQL query
execute_query() {
    local query="$1"
    local output_file="$2"
    
    psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -A -F"," -c "$query" > "$output_file" 2>&1
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error executing query. Check database connection.${NC}"
        cat "$output_file"
        exit 1
    fi
}

# ==============================================================
# 1. List all existing indexes
# ==============================================================
echo -e "${YELLOW}1. Analyzing existing indexes...${NC}"

QUERY_EXISTING="
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"

execute_query "$QUERY_EXISTING" "$EXISTING_INDEXES"

TOTAL_INDEXES=$(wc -l < "$EXISTING_INDEXES")
echo -e "   Found ${GREEN}$TOTAL_INDEXES${NC} indexes"

# ==============================================================
# 2. Find unused indexes (never scanned)
# ==============================================================
echo -e "${YELLOW}2. Checking for unused indexes...${NC}"

QUERY_UNUSED="
SELECT 
    schemaname || '.' || relname AS table,
    indexrelname AS index,
    idx_scan AS scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public'
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
"

execute_query "$QUERY_UNUSED" "$UNUSED_INDEXES"

UNUSED_COUNT=$(wc -l < "$UNUSED_INDEXES")
if [ "$UNUSED_COUNT" -gt 0 ]; then
    echo -e "   Found ${RED}$UNUSED_COUNT${NC} unused indexes"
else
    echo -e "   ${GREEN}No unused indexes found${NC}"
fi

# ==============================================================
# 3. Get table statistics (row counts, sizes)
# ==============================================================
echo -e "${YELLOW}3. Gathering table statistics...${NC}"

QUERY_STATS="
SELECT 
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup AS row_count,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

execute_query "$QUERY_STATS" "$TABLE_STATS"
TABLE_COUNT=$(wc -l < "$TABLE_STATS")
echo -e "   Analyzed ${GREEN}$TABLE_COUNT${NC} tables"

# ==============================================================
# 4. Check for missing indexes on critical tables
# ==============================================================
echo -e "${YELLOW}4. Checking for missing indexes on critical tables...${NC}"

# Define critical tables and their expected indexes
declare -A CRITICAL_INDEXES=(
    ["sessions"]="tenant_id,created_at|user_id,created_at"
    ["audit_logs"]="tenant_id,timestamp|user_id,timestamp|event_type,timestamp"
    ["locks"]="resource,tenant_id|acquired_at"
    ["tenant_user_identifiers"]="identifier_value,platform|tenant_id"
)

echo "" > "$MISSING_INDEXES"

for table in "${!CRITICAL_INDEXES[@]}"; do
    IFS='|' read -ra EXPECTED_INDEXES <<< "${CRITICAL_INDEXES[$table]}"
    
    for expected_index in "${EXPECTED_INDEXES[@]}"; do
        # Check if composite index exists
        IFS=',' read -ra COLUMNS <<< "$expected_index"
        
        # Query to check if index exists on these columns
        CHECK_QUERY="
        SELECT COUNT(*) 
        FROM pg_indexes 
        WHERE tablename = '$table' 
          AND schemaname = 'public'
          AND (
        "
        
        for i in "${!COLUMNS[@]}"; do
            col="${COLUMNS[$i]}"
            if [ $i -gt 0 ]; then
                CHECK_QUERY="$CHECK_QUERY OR "
            fi
            CHECK_QUERY="$CHECK_QUERY indexdef LIKE '%$col%'"
        done
        
        CHECK_QUERY="$CHECK_QUERY );"
        
        RESULT=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DATABASE" -t -A -c "$CHECK_QUERY" 2>/dev/null || echo "0")
        
        if [ "$RESULT" = "0" ]; then
            echo "MISSING: CREATE INDEX idx_${table}_${expected_index//,/_} ON $table(${expected_index//,/, });" >> "$MISSING_INDEXES"
        fi
    done
done

MISSING_COUNT=$(wc -l < "$MISSING_INDEXES")
if [ "$MISSING_COUNT" -gt 0 ]; then
    echo -e "   Found ${RED}$MISSING_COUNT${NC} missing recommended indexes"
else
    echo -e "   ${GREEN}All recommended indexes exist${NC}"
fi

# ==============================================================
# 5. Check for duplicate indexes
# ==============================================================
echo -e "${YELLOW}5. Checking for duplicate indexes...${NC}"

QUERY_DUPLICATES="
SELECT 
    array_agg(indexname) AS duplicate_indexes,
    tablename,
    array_agg(indexdef) AS definitions
FROM pg_indexes
WHERE schemaname = 'public'
GROUP BY tablename, indexdef
HAVING COUNT(*) > 1;
"

DUPLICATES_FILE="$TEMP_DIR/duplicates.txt"
execute_query "$QUERY_DUPLICATES" "$DUPLICATES_FILE"

DUPLICATE_COUNT=$(wc -l < "$DUPLICATES_FILE")
if [ "$DUPLICATE_COUNT" -gt 0 ]; then
    echo -e "   Found ${RED}$DUPLICATE_COUNT${NC} duplicate index definitions"
else
    echo -e "   ${GREEN}No duplicate indexes found${NC}"
fi

# ==============================================================
# 6. Generate JSON report
# ==============================================================
echo ""
echo -e "${YELLOW}6. Generating JSON report...${NC}"

# Start JSON
cat > "$OUTPUT_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "database": {
    "host": "$HOST",
    "port": $PORT,
    "database": "$DATABASE"
  },
  "summary": {
    "total_indexes": $TOTAL_INDEXES,
    "unused_indexes": $UNUSED_COUNT,
    "missing_indexes": $MISSING_COUNT,
    "duplicate_indexes": $DUPLICATE_COUNT,
    "tables_analyzed": $TABLE_COUNT
  },
  "existing_indexes": [
EOF

# Add existing indexes
first=true
while IFS=',' read -r schema table index def; do
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$OUTPUT_FILE"
    fi
    cat >> "$OUTPUT_FILE" <<EOF
    {
      "schema": "$schema",
      "table": "$table",
      "index": "$index",
      "definition": $(echo "$def" | jq -Rs .)
    }
EOF
done < "$EXISTING_INDEXES"

cat >> "$OUTPUT_FILE" <<EOF

  ],
  "unused_indexes": [
EOF

# Add unused indexes
first=true
while IFS=',' read -r table index scans size; do
    if [ -n "$table" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$OUTPUT_FILE"
        fi
        cat >> "$OUTPUT_FILE" <<EOF
    {
      "table": "$table",
      "index": "$index",
      "scans": $scans,
      "size": "$size",
      "recommendation": "Consider dropping this index if not needed for constraints"
    }
EOF
    fi
done < "$UNUSED_INDEXES"

cat >> "$OUTPUT_FILE" <<EOF

  ],
  "table_statistics": [
EOF

# Add table statistics
first=true
while IFS=',' read -r table total_size table_size index_size rows inserts updates deletes; do
    if [ -n "$table" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$OUTPUT_FILE"
        fi
        cat >> "$OUTPUT_FILE" <<EOF
    {
      "table": "$table",
      "total_size": "$total_size",
      "table_size": "$table_size",
      "indexes_size": "$index_size",
      "row_count": $rows,
      "operations": {
        "inserts": $inserts,
        "updates": $updates,
        "deletes": $deletes
      }
    }
EOF
    fi
done < "$TABLE_STATS"

cat >> "$OUTPUT_FILE" <<EOF

  ],
  "missing_indexes": [
EOF

# Add missing indexes
first=true
while IFS= read -r missing_index; do
    if [ -n "$missing_index" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$OUTPUT_FILE"
        fi
        # Extract table and columns from CREATE INDEX statement
        table=$(echo "$missing_index" | sed -n 's/.*ON \([^ ]*\)(.*/\1/p')
        columns=$(echo "$missing_index" | sed -n 's/.*(\(.*\));/\1/p')
        index_name=$(echo "$missing_index" | sed -n 's/CREATE INDEX \([^ ]*\) .*/\1/p')
        
        cat >> "$OUTPUT_FILE" <<EOF
    {
      "table": "$table",
      "columns": "$columns",
      "index_name": "$index_name",
      "sql": $(echo "$missing_index" | jq -Rs .),
      "priority": "high",
      "reason": "Frequently filtered/joined columns without composite index"
    }
EOF
    fi
done < "$MISSING_INDEXES"

cat >> "$OUTPUT_FILE" <<EOF

  ],
  "recommendations": [
EOF

# Generate recommendations
RECOMMENDATIONS=()

if [ "$MISSING_COUNT" -gt 0 ]; then
    RECOMMENDATIONS+=('{"severity": "high", "category": "missing_indexes", "message": "Add missing composite indexes on critical tables to improve query performance", "action": "Review missing_indexes section and execute CREATE INDEX statements"}')
fi

if [ "$UNUSED_COUNT" -gt 0 ]; then
    RECOMMENDATIONS+=('{"severity": "medium", "category": "unused_indexes", "message": "Consider dropping unused indexes to reduce write overhead and disk usage", "action": "Review unused_indexes section and DROP unnecessary indexes"}')
fi

if [ "$DUPLICATE_COUNT" -gt 0 ]; then
    RECOMMENDATIONS+=('{"severity": "medium", "category": "duplicate_indexes", "message": "Duplicate index definitions found - only one is needed", "action": "DROP redundant indexes keeping the most descriptive name"}')
fi

# Add recommendations based on table statistics
while IFS=',' read -r table total_size table_size index_size rows inserts updates deletes; do
    if [ -n "$table" ] && [ "$rows" -gt 10000 ]; then
        # Large tables need indexes
        RECOMMENDATIONS+=("{\"severity\": \"info\", \"category\": \"large_table\", \"message\": \"Table $table has $rows rows - ensure critical queries are indexed\", \"action\": \"Review query patterns and add indexes for WHERE/JOIN clauses\"}")
    fi
done < "$TABLE_STATS"

# Write recommendations
first=true
for rec in "${RECOMMENDATIONS[@]}"; do
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$OUTPUT_FILE"
    fi
    echo "    $rec" >> "$OUTPUT_FILE"
done

cat >> "$OUTPUT_FILE" <<EOF

  ]
}
EOF

# ==============================================================
# 7. Display summary
# ==============================================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Analysis Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Summary:${NC}"
echo "  Total Indexes: $TOTAL_INDEXES"
echo "  Unused Indexes: $UNUSED_COUNT"
echo "  Missing Recommended Indexes: $MISSING_COUNT"
echo "  Duplicate Indexes: $DUPLICATE_COUNT"
echo "  Tables Analyzed: $TABLE_COUNT"
echo ""

if [ "$MISSING_COUNT" -gt 0 ]; then
    echo -e "${RED}⚠️  Missing Indexes Found:${NC}"
    cat "$MISSING_INDEXES"
    echo ""
fi

if [ "$UNUSED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}💡 Unused Indexes (consider dropping):${NC}"
    while IFS=',' read -r table index scans size; do
        if [ -n "$table" ]; then
            echo "   DROP INDEX $index; -- Table: $table, Size: $size"
        fi
    done < "$UNUSED_INDEXES"
    echo ""
fi

echo -e "${GREEN}✓ Full report saved to: $OUTPUT_FILE${NC}"
echo ""
echo -e "${BLUE}Recommendations:${NC}"

if [ "$MISSING_COUNT" -gt 0 ]; then
    echo -e "  ${RED}🚨 HIGH:${NC} Add missing composite indexes to improve query performance"
fi

if [ "$UNUSED_COUNT" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠️  MEDIUM:${NC} Drop unused indexes to reduce write overhead"
fi

if [ "$DUPLICATE_COUNT" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠️  MEDIUM:${NC} Remove duplicate index definitions"
fi

echo -e "  ${BLUE}💡 INFO:${NC} Review table statistics for optimization opportunities"
echo ""

# Cleanup
rm -rf "$TEMP_DIR"
unset PGPASSWORD

echo -e "${GREEN}Done!${NC}"
