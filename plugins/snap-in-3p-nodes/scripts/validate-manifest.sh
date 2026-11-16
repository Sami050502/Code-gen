# Validate DevRev snap-in manifest.yaml for 3P node operations
# Based on manifest-schema.md validation rules

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
ERRORS=0
WARNINGS=0

# Valid entity types for id_type
VALID_ID_TYPES=("ticket" "issue" "contact" "devu" "revu" "group" "opportunity" "product" "capability" "feature" "enhancement" "account" "rev_org" "service_account" "article")

# Helper functions
error() {
    echo -e "${RED}ERROR: $1${NC}"
    ((ERRORS++))
}

warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
    ((WARNINGS++))
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}  $1${NC}"
}

# Find manifest.yaml
MANIFEST_PATH="${1:-manifest.yaml}"

if [ ! -f "$MANIFEST_PATH" ]; then
    MANIFEST_PATH="./manifest.yaml"
    if [ ! -f "$MANIFEST_PATH" ]; then
        MANIFEST_PATH="../manifest.yaml"
        if [ ! -f "$MANIFEST_PATH" ]; then
            error "manifest.yaml not found. Usage: $0 [path-to-manifest.yaml]"
            exit 1
        fi
    fi
fi

echo -e "${BLUE}Validating: $MANIFEST_PATH${NC}"
echo ""

# Check 1: Valid YAML syntax
echo "1. Checking YAML syntax..."
if command -v yq &> /dev/null; then
    if yq eval '.' "$MANIFEST_PATH" > /dev/null 2>&1; then
        success "Valid YAML syntax"
    else
        error "Invalid YAML syntax"
        exit 1
    fi
elif command -v python3 &> /dev/null; then
    if python3 -c "import yaml; yaml.safe_load(open('$MANIFEST_PATH'))" 2>/dev/null; then
        success "Valid YAML syntax"
    else
        error "Invalid YAML syntax"
        exit 1
    fi
else
    warning "Cannot validate YAML syntax (yq or python3 not found)"
fi

# Check 2: Required top-level fields
echo ""
echo "2. Checking required top-level fields..."
REQUIRED_FIELDS=("name" "version")
for field in "${REQUIRED_FIELDS[@]}"; do
    if grep -q "^$field:" "$MANIFEST_PATH"; then
        success "Found required field: $field"
    else
        error "Missing required top-level field: $field"
    fi
done

# Check 3: Operations section
echo ""
echo "3. Checking operations section..."
if grep -q "^operations:" "$MANIFEST_PATH"; then
    success "Found operations section"
    
    # Count operations
    OP_COUNT=$(grep -c "^  - name:" "$MANIFEST_PATH" || echo "0")
    if [ "$OP_COUNT" -eq "0" ]; then
        error "No operations found in operations section"
    else
        info "Found $OP_COUNT operation(s)"
    fi
else
    error "Missing 'operations:' section"
    exit 1
fi

# Check 4: Unsupported field types
echo ""
echo "4. Checking for unsupported field types..."
UNSUPPORTED_TYPES=("enum" "rich_text" "object" "date" "datetime")
FOUND_UNSUPPORTED=0
for type in "${UNSUPPORTED_TYPES[@]}"; do
    if grep -q "field_type: $type" "$MANIFEST_PATH"; then
        error "Unsupported field_type '$type' found"
        info "  Use 'array' with 'base_type: enum' instead of 'enum'"
        info "  Use 'array' with 'base_type: composite' instead of 'object'"
        info "  Use 'text' for dates (ISO 8601 format) instead of 'date'/'datetime'"
        FOUND_UNSUPPORTED=1
    fi
done

if [ $FOUND_UNSUPPORTED -eq 0 ]; then
    success "No unsupported field types found"
fi

# Check 5: Supported field types only
echo ""
echo "5. Checking field types are supported..."
SUPPORTED_TYPES=("id" "text" "array" "bool" "int")
if grep -q "field_type:" "$MANIFEST_PATH"; then
    ALL_FIELD_TYPES=$(grep "field_type:" "$MANIFEST_PATH" | sed 's/.*field_type: //' | xargs)
    for field_type in $ALL_FIELD_TYPES; do
        if [[ ! " ${SUPPORTED_TYPES[@]} " =~ " ${field_type} " ]]; then
            if [[ ! " ${UNSUPPORTED_TYPES[@]} " =~ " ${field_type} " ]]; then
                warning "Unknown field_type '$field_type' found (may be unsupported)"
            fi
        fi
    done
fi

# Check 6: id fields have id_type
echo ""
echo "6. Checking id field types..."
ID_FIELDS=$(grep -n "field_type: id" "$MANIFEST_PATH" | cut -d: -f1 || echo "")
if [ -n "$ID_FIELDS" ]; then
    for line_num in $ID_FIELDS; do
        # Get field name
        FIELD_NAME=$(sed -n "${line_num}p" "$MANIFEST_PATH" | grep -o "name: [^ ]*" | sed 's/name: //' || echo "unknown")
        
        # Check if id_type exists within next 10 lines
        CONTEXT=$(sed -n "${line_num},$((line_num+10))p" "$MANIFEST_PATH")
        if echo "$CONTEXT" | grep -q "id_type:"; then
            # Extract id_type values
            ID_TYPE_LINE=$(echo "$CONTEXT" | grep "id_type:" | head -1)
            ID_TYPES=$(echo "$ID_TYPE_LINE" | sed 's/.*id_type: *\[\(.*\)\].*/\1/' | tr ',' ' ' | xargs)
            
            if [ -z "$ID_TYPES" ]; then
                error "id field '$FIELD_NAME' at line $line_num has empty id_type array"
            else
                # Validate each id_type value
                INVALID_TYPES=""
                for id_type in $ID_TYPES; do
                    if [[ ! " ${VALID_ID_TYPES[@]} " =~ " ${id_type} " ]]; then
                        INVALID_TYPES="$INVALID_TYPES $id_type"
                    fi
                done
                
                if [ -n "$INVALID_TYPES" ]; then
                    error "id field '$FIELD_NAME' at line $line_num has invalid id_type(s):$INVALID_TYPES"
                    info "  Valid id_type values: ${VALID_ID_TYPES[*]}"
                else
                    success "id field '$FIELD_NAME' at line $line_num has valid id_type"
                fi
            fi
        else
            error "id field '$FIELD_NAME' at line $line_num is missing required 'id_type' array"
        fi
    done
else
    info "No id fields found"
fi

# Check 7: array fields have base_type
echo ""
echo "7. Checking array field types..."
ARRAY_FIELDS=$(grep -n "field_type: array" "$MANIFEST_PATH" | cut -d: -f1 || echo "")
if [ -n "$ARRAY_FIELDS" ]; then
    for line_num in $ARRAY_FIELDS; do
        # Get field name
        FIELD_NAME=$(sed -n "${line_num}p" "$MANIFEST_PATH" | grep -o "name: [^ ]*" | sed 's/name: //' || echo "unknown")
        
        # Check if base_type exists within next 10 lines
        CONTEXT=$(sed -n "${line_num},$((line_num+10))p" "$MANIFEST_PATH")
        if echo "$CONTEXT" | grep -q "base_type:"; then
            BASE_TYPE=$(echo "$CONTEXT" | grep "base_type:" | head -1 | sed 's/.*base_type: //' | xargs)
            
            case "$BASE_TYPE" in
                "text")
                    success "array field '$FIELD_NAME' at line $line_num has base_type: text"
                    ;;
                "enum")
                    # Check for allowed_values
                    if echo "$CONTEXT" | grep -q "allowed_values:"; then
                        ALLOWED_VALS=$(echo "$CONTEXT" | grep "allowed_values:" | head -1 | sed 's/.*allowed_values: *\[\(.*\)\].*/\1/' | tr ',' ' ' | xargs)
                        VAL_COUNT=$(echo "$ALLOWED_VALS" | wc -w | xargs)
                        if [ "$VAL_COUNT" -lt 2 ]; then
                            error "enum array '$FIELD_NAME' at line $line_num has less than 2 allowed_values"
                        else
                            success "array field '$FIELD_NAME' at line $line_num has base_type: enum with $VAL_COUNT allowed_values"
                            
                            # Check default_value if present
                            if echo "$CONTEXT" | grep -q "default_value:"; then
                                DEFAULT_VAL=$(echo "$CONTEXT" | grep "default_value:" | head -1 | sed 's/.*default_value: *\[\(.*\)\].*/\1/' | tr ',' ' ' | xargs)
                                for val in $DEFAULT_VAL; do
                                    if [[ ! " $ALLOWED_VALS " =~ " $val " ]]; then
                                        warning "enum array '$FIELD_NAME' default_value '$val' not in allowed_values"
                                    fi
                                done
                            fi
                        fi
                    else
                        error "enum array '$FIELD_NAME' at line $line_num is missing required 'allowed_values'"
                    fi
                    ;;
                "composite")
                    # Check for composite_type
                    if echo "$CONTEXT" | grep -q "composite_type:"; then
                        COMPOSITE_TYPE=$(echo "$CONTEXT" | grep "composite_type:" | head -1 | sed 's/.*composite_type: //' | xargs)
                        success "array field '$FIELD_NAME' at line $line_num has base_type: composite with type '$COMPOSITE_TYPE'"
                        
                        # Check if composite definition exists (in inputs.composites or outputs.composites)
                        if grep -q "composites:" "$MANIFEST_PATH"; then
                            if grep -A 20 "composites:" "$MANIFEST_PATH" | grep -q "name: $COMPOSITE_TYPE"; then
                                success "  Composite type '$COMPOSITE_TYPE' is defined"
                            else
                                error "  Composite type '$COMPOSITE_TYPE' referenced but not defined in composites section"
                            fi
                        else
                            error "  Composite type '$COMPOSITE_TYPE' referenced but no composites section found"
                        fi
                    else
                        error "composite array '$FIELD_NAME' at line $line_num is missing required 'composite_type'"
                    fi
                    ;;
                *)
                    error "array field '$FIELD_NAME' at line $line_num has invalid base_type '$BASE_TYPE' (must be: text, enum, or composite)"
                    ;;
            esac
        else
            error "array field '$FIELD_NAME' at line $line_num is missing required 'base_type'"
        fi
    done
else
    info "No array fields found"
fi

# Check 8: Operation structure
echo ""
echo "8. Checking operation structure..."
OPERATIONS=$(grep -n "^  - name:" "$MANIFEST_PATH" | cut -d: -f1 || echo "")
if [ -n "$OPERATIONS" ]; then
    for line_num in $OPERATIONS; do
        # Get operation name
        OP_NAME=$(sed -n "${line_num}p" "$MANIFEST_PATH" | sed 's/.*name: //' | xargs)
        
        # Check for required operation fields within next 80 lines
        CONTEXT=$(sed -n "${line_num},$((line_num+80))p" "$MANIFEST_PATH")
        
        OP_ERRORS=0
        echo ""
        info "Checking operation: $OP_NAME"
        
        # Required fields
        REQUIRED_OP_FIELDS=("display_name" "description" "slug" "function" "type" "inputs" "outputs")
        for field in "${REQUIRED_OP_FIELDS[@]}"; do
            if echo "$CONTEXT" | grep -q "^    $field:" || echo "$CONTEXT" | grep -q "^      $field:"; then
                success "  Has $field"
            else
                error "  Operation '$OP_NAME' missing required field: $field"
                ((OP_ERRORS++))
            fi
        done
        
        # Validate type is 'action'
        if echo "$CONTEXT" | grep -q "type:"; then
            OP_TYPE=$(echo "$CONTEXT" | grep "type:" | head -1 | sed 's/.*type: //' | xargs)
            if [ "$OP_TYPE" = "action" ]; then
                success "  Type is 'action' (correct)"
            else
                error "  Operation '$OP_NAME' has type '$OP_TYPE' (must be 'action')"
                ((OP_ERRORS++))
            fi
        fi
        
        # Validate function is 'operation_handler'
        if echo "$CONTEXT" | grep -q "function:"; then
            FUNCTION=$(echo "$CONTEXT" | grep "function:" | head -1 | sed 's/.*function: //' | xargs)
            if [ "$FUNCTION" = "operation_handler" ]; then
                success "  Function is 'operation_handler' (correct)"
            else
                warning "  Function is '$FUNCTION' (expected 'operation_handler')"
            fi
        fi
        
        # Check inputs and outputs have fields
        if echo "$CONTEXT" | grep -q "inputs:"; then
            INPUTS_CONTEXT=$(echo "$CONTEXT" | sed -n '/inputs:/,/outputs:/p' | head -20)
            if echo "$INPUTS_CONTEXT" | grep -q "fields:"; then
                INPUT_FIELD_COUNT=$(echo "$INPUTS_CONTEXT" | grep -c "  - name:" || echo "0")
                if [ "$INPUT_FIELD_COUNT" -eq "0" ]; then
                    warning "  Operation '$OP_NAME' has no input fields"
                else
                    success "  Has $INPUT_FIELD_COUNT input field(s)"
                fi
            else
                warning "  Operation '$OP_NAME' inputs section missing 'fields:'"
            fi
        fi
        
        if echo "$CONTEXT" | grep -q "outputs:"; then
            OUTPUTS_CONTEXT=$(echo "$CONTEXT" | sed -n '/outputs:/,$p' | head -20)
            if echo "$OUTPUTS_CONTEXT" | grep -q "fields:"; then
                OUTPUT_FIELD_COUNT=$(echo "$OUTPUTS_CONTEXT" | grep -c "  - name:" || echo "0")
                if [ "$OUTPUT_FIELD_COUNT" -eq "0" ]; then
                    warning "  Operation '$OP_NAME' has no output fields"
                else
                    success "  Has $OUTPUT_FIELD_COUNT output field(s)"
                fi
            else
                warning "  Operation '$OP_NAME' outputs section missing 'fields:'"
            fi
        fi
        
        if [ $OP_ERRORS -eq 0 ]; then
            success "  Operation '$OP_NAME' structure is valid"
        fi
    done
fi

# Check 9: Field structure (name, field_type, description)
echo ""
echo "9. Checking field structure..."
ALL_FIELDS=$(grep -n "  - name:" "$MANIFEST_PATH" | grep -v "^  - name:" | cut -d: -f1 || echo "")
if [ -n "$ALL_FIELDS" ]; then
    for line_num in $ALL_FIELDS; do
        # Get field name
        FIELD_NAME=$(sed -n "${line_num}p" "$MANIFEST_PATH" | sed 's/.*name: //' | xargs)
        
        # Check context for required fields
        CONTEXT=$(sed -n "${line_num},$((line_num+15))p" "$MANIFEST_PATH")
        
        if ! echo "$CONTEXT" | grep -q "field_type:"; then
            error "Field '$FIELD_NAME' at line $line_num is missing 'field_type'"
        fi
        
        if ! echo "$CONTEXT" | grep -q "description:"; then
            warning "Field '$FIELD_NAME' at line $line_num is missing 'description'"
        fi
    done
fi

# Check 10: Common mistakes
echo ""
echo "10. Checking for common mistakes..."

# Check for wrong words that might indicate wrong API usage
if grep -qi "enhancement.*work" "$MANIFEST_PATH" || grep -qi "worksCreate.*enhancement" "$MANIFEST_PATH"; then
    warning "Found 'enhancement' near 'work' - remember Enhancement is a Part, not a Work! Use partsCreate, not worksCreate"
fi

# Check for missing display_name in ui sections
if grep -q "ui:" "$MANIFEST_PATH"; then
    UI_SECTIONS=$(grep -n "ui:" "$MANIFEST_PATH" | cut -d: -f1)
    for line_num in $UI_SECTIONS; do
        CONTEXT=$(sed -n "${line_num},$((line_num+5))p" "$MANIFEST_PATH")
        if ! echo "$CONTEXT" | grep -q "display_name:"; then
            warning "ui section at line $line_num might be missing 'display_name'"
        fi
    done
fi

# Final summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Manifest validation passed!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Note: $WARNINGS warning(s) found. Review recommended.${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ Manifest validation failed with $ERRORS error(s)${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Also found $WARNINGS warning(s).${NC}"
    fi
    exit 1
fi
