#!/bin/bash

# ============================================================
# Author: Sagar Malla
# Email:  sagarmalla08@gmail.com
# Date:   13-MAY, 2025
# Description:
#   Function-based script to generate CA and SAN certificates
#   for a user-specified wildcard DNS. Used for Elasticsearch,
#   Kibana, and Logstash in test/prod environments.
# ============================================================

set -euo pipefail

# ─────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# ─────────────────────────────────────────────
#  GLOBAL CONSTANTS
# ─────────────────────────────────────────────
CERTS_DIR="/etc/elasticsearch/certs"
ELASTICSEARCH_BIN="/usr/share/elasticsearch/bin/elasticsearch-certutil"
KEYSTORE_BIN="/usr/share/elasticsearch/bin/elasticsearch-keystore"
CHAR_SET='A-Za-z0-9@#*\-+!'

# Will be set by functions
USER_DOMAIN=""
WILDCARD=""
RANDOM_PASS=""
HOST_IP=""

# ─────────────────────────────────────────────
#  LOGGING HELPERS
# ─────────────────────────────────────────────
log_info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
log_success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
log_step()    { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════${RESET}"; \
                echo -e "${BOLD}${BLUE}  ▶  $*${RESET}"; \
                echo -e "${BOLD}${BLUE}══════════════════════════════════════════════${RESET}"; }
log_cmd()     { echo -e "${DIM}  $ $*${RESET}"; }

# ─────────────────────────────────────────────
#  ERROR TRAP
# ─────────────────────────────────────────────
trap_error() {
    local exit_code=$?
    local line_no=$1
    echo ""
    log_error "──────────────────────────────────────────────"
    log_error " Script failed at line ${BOLD}${line_no}${RESET}${RED} with exit code ${BOLD}${exit_code}"
    log_error "──────────────────────────────────────────────"
    echo -e "${YELLOW}  Tip: Check the output above for the root cause.${RESET}"
    echo ""
    exit "$exit_code"
}
trap 'trap_error $LINENO' ERR

# ─────────────────────────────────────────────
#  PRINT BANNER
# ─────────────────────────────────────────────
print_banner() {
    echo -e "${BOLD}${MAGENTA}"
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║        ELK Stack Certificate Generator            ║"
    echo "  ║     Elasticsearch · Kibana · Logstash             ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "  ${DIM}Author : Sagar Malla <sagarmalla08@gmail.com>${RESET}"
    echo -e "  ${DIM}Date   : $(date '+%d-%b, %Y')${RESET}"
    echo ""
}

# ─────────────────────────────────────────────
#  BACKUP /etc/elasticsearch DIRECTORY
# ─────────────────────────────────────────────
backup_elasticsearch_dir() {
    log_step "Backing Up /etc/elasticsearch Directory"

    local src="/etc/elasticsearch"
    local timestamp
    timestamp=$(date '+%y%m%d_%H%M%S')
    local dest="/etc/elasticsearch_${timestamp}"

    if [ ! -d "$src" ]; then
        log_warn "Source directory ${BOLD}$src${RESET}${YELLOW} does not exist. Skipping full backup."
        return 0
    fi

    log_info "Copying ${BOLD}$src${RESET} → ${BOLD}$dest${RESET} ..."
    if ! sudo cp -a "$src" "$dest"; then
        log_error "Failed to back up $src to $dest"
        exit 1
    fi

    # Verify backup size matches source
    local src_size dest_size
    src_size=$(sudo du -sb "$src" 2>/dev/null | awk '{print $1}')
    dest_size=$(sudo du -sb "$dest" 2>/dev/null | awk '{print $1}')

    if [ "$src_size" != "$dest_size" ]; then
        log_warn "Backup size mismatch — src: ${src_size}B vs dest: ${dest_size}B. Verify manually."
    else
        log_success "Backup verified — size: ${BOLD}$(sudo du -sh "$dest" | awk '{print $1}')${RESET}"
    fi

    log_success "Full backup saved to: ${BOLD}$dest${RESET}"
    echo -e "  ${DIM}Ownership and permissions preserved via cp -a${RESET}"
}

# ─────────────────────────────────────────────
#  CHECK PREREQUISITES
# ─────────────────────────────────────────────
check_prerequisites() {
    log_step "Checking Prerequisites"

    local missing=0

    for cmd in openssl keytool sudo unzip tr awk; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "Required command not found: ${BOLD}$cmd"
            missing=$((missing + 1))
        else
            log_success "Found: ${BOLD}$cmd${RESET} → $(command -v "$cmd")"
        fi
    done

    if [ ! -x "$ELASTICSEARCH_BIN" ]; then
        log_error "elasticsearch-certutil not found at: ${BOLD}$ELASTICSEARCH_BIN"
        missing=$((missing + 1))
    else
        log_success "Found: ${BOLD}elasticsearch-certutil"
    fi

    if [ ! -x "$KEYSTORE_BIN" ]; then
        log_error "elasticsearch-keystore not found at: ${BOLD}$KEYSTORE_BIN"
        missing=$((missing + 1))
    else
        log_success "Found: ${BOLD}elasticsearch-keystore"
    fi

    if [ "$missing" -gt 0 ]; then
        log_error "Missing $missing prerequisite(s). Aborting."
        exit 1
    fi

    log_success "All prerequisites satisfied."
}

# ─────────────────────────────────────────────
#  BACKUP EXISTING CERTS
# ─────────────────────────────────────────────
backup_existing_certs() {
    log_step "Backing Up Existing Certificates"

    local backup_dir="$CERTS_DIR/backup"
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local versioned_backup="${backup_dir}/${timestamp}"

    sudo mkdir -p "$versioned_backup"
    sudo chown root:elasticsearch "$versioned_backup" || true
    sudo chmod 770 "$versioned_backup"

    local count=0
    while IFS= read -r -d '' file; do
        sudo mv "$file" "$versioned_backup/"
        log_info "Moved: ${BOLD}$(basename "$file")${RESET} → backup/${timestamp}/"
        count=$((count + 1))
    done < <(sudo find "$CERTS_DIR" -maxdepth 1 -type f \
                ! -name "http_ca.crt" \
                ! -name "http.p12" \
                ! -name "transport.p12" \
                -print0 2>/dev/null)

    if [ "$count" -eq 0 ]; then
        log_info "No existing certificates found to back up."
    else
        log_success "Backed up ${BOLD}${count}${RESET}${GREEN} file(s) to: ${BOLD}backup/${timestamp}/"
    fi
}

# ─────────────────────────────────────────────
#  PROMPT FOR DOMAIN
# ─────────────────────────────────────────────
prompt_domain() {
    log_step "Domain Configuration"

    while true; do
        echo -en "${WHITE}  Enter your base domain ${DIM}(e.g. sagar.com.np or sagar.com)${RESET}${WHITE}: ${RESET}"
        read -r USER_DOMAIN

        if [[ "$USER_DOMAIN" =~ ^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$ ]]; then
            break
        else
            log_warn "Invalid domain format. Please try again."
        fi
    done

    WILDCARD="*.$USER_DOMAIN"
    HOST_IP=$(hostname -I | awk '{print $1}')

    log_success "Base domain  : ${BOLD}$USER_DOMAIN"
    log_success "Wildcard SAN : ${BOLD}$WILDCARD"
    log_success "Host IP      : ${BOLD}$HOST_IP"
}

# ─────────────────────────────────────────────
#  GENERATE RANDOM PASSWORD
# ─────────────────────────────────────────────
generate_password() {
    log_step "Generating Secure Password"

    # Temporarily disable pipefail: `tr | head` triggers SIGPIPE when head exits
    # after reading 20 bytes. Under `set -o pipefail` that non-zero exit kills the script.
    set +o pipefail
    RANDOM_PASS=$(tr -dc "$CHAR_SET" </dev/urandom | head -c 20)
    set -o pipefail

    if [ -z "$RANDOM_PASS" ]; then
        log_error "Failed to generate a random password."
        exit 1
    fi

    local timestamp
    timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    echo "$timestamp - $RANDOM_PASS" >> pass.txt

    log_success "Password generated and saved to: ${BOLD}pass.txt"
    echo -e "  ${YELLOW}⚠  Generated Password: ${BOLD}${RANDOM_PASS}${RESET}"
    echo -e "  ${DIM}  (CA password = Node cert password = Truststore password)${RESET}"
}

# ─────────────────────────────────────────────
#  CREATE CERTS DIRECTORY
# ─────────────────────────────────────────────
create_certs_dir() {
    log_step "Preparing Certificates Directory"

    sudo mkdir -p "$CERTS_DIR"
    log_success "Certs directory ready: ${BOLD}$CERTS_DIR"
}

# ─────────────────────────────────────────────
#  CREATE INSTANCES.YML
# ─────────────────────────────────────────────
create_instances_yml() {
    log_step "Creating instances.yml (SAN Configuration)"

    cat <<EOF | sudo tee "$CERTS_DIR/instances.yml" >/dev/null
instances:
  - name: "$USER_DOMAIN"
    dns:
      - "$WILDCARD"
      - "$USER_DOMAIN"
      - "localhost"
      - "ett-elk"
    ip:
      - "$HOST_IP"
EOF

    log_success "instances.yml written to: ${BOLD}$CERTS_DIR/instances.yml"
    echo -e "${DIM}"
    sudo cat "$CERTS_DIR/instances.yml" | sed 's/^/    /'
    echo -e "${RESET}"
}

# ─────────────────────────────────────────────
#  CREATE CA
# ─────────────────────────────────────────────
create_ca() {
    log_step "Creating Certificate Authority (CA)"

    if [ -f "$CERTS_DIR/elastic-stack-ca.p12" ]; then
        log_warn "CA already exists at ${BOLD}$CERTS_DIR/elastic-stack-ca.p12${RESET}${YELLOW}. Skipping CA generation."
        return 0
    fi

    log_info "Generating CA — valid for 10 years (3650 days)..."
    log_cmd "$ELASTICSEARCH_BIN ca --days 3650 --out $CERTS_DIR/elastic-stack-ca.p12 --pass ****"

    if ! sudo "$ELASTICSEARCH_BIN" ca \
            --days 3650 \
            --out "$CERTS_DIR/elastic-stack-ca.p12" \
            --pass "$RANDOM_PASS" 2>&1; then
        log_error "CA generation failed."
        exit 1
    fi

    log_success "CA created: ${BOLD}$CERTS_DIR/elastic-stack-ca.p12"
}

# ─────────────────────────────────────────────
#  GENERATE NODE CERTIFICATE
# ─────────────────────────────────────────────
generate_node_cert() {
    log_step "Generating Node Certificate (SAN)"

    log_info "Generating node cert — valid for 10 years (3650 days)..."
    log_cmd "$ELASTICSEARCH_BIN cert --ca ... --in instances.yml --out $USER_DOMAIN.zip --days 3650"

    if ! sudo "$ELASTICSEARCH_BIN" cert \
            --ca "$CERTS_DIR/elastic-stack-ca.p12" \
            --ca-pass "$RANDOM_PASS" \
            --in "$CERTS_DIR/instances.yml" \
            --out "$CERTS_DIR/$USER_DOMAIN.zip" \
            --pass "$RANDOM_PASS" \
            --days 3650 2>&1; then
        log_error "Node certificate generation failed."
        exit 1
    fi

    log_success "Node certificate created: ${BOLD}$CERTS_DIR/$USER_DOMAIN.zip"
}

# ─────────────────────────────────────────────
#  EXTRACT AND ORGANISE CERT FILES
# ─────────────────────────────────────────────
extract_certs() {
    log_step "Extracting and Organising Certificate Files"

    cd "$CERTS_DIR"

    log_info "Unzipping: ${BOLD}$USER_DOMAIN.zip"
    sudo unzip -o "$USER_DOMAIN.zip"

    if [ -d "$CERTS_DIR/$USER_DOMAIN" ]; then
        sudo mv "$CERTS_DIR/$USER_DOMAIN"/* "$CERTS_DIR/"
        sudo rm -rf "$CERTS_DIR/$USER_DOMAIN"
        log_success "Moved files from sub-directory to: ${BOLD}$CERTS_DIR"
    fi

    # Extract CA cert and key
    log_info "Extracting CA certificate (PEM)..."
    if ! sudo openssl pkcs12 \
            -in "$CERTS_DIR/elastic-stack-ca.p12" \
            -out "$CERTS_DIR/ca_${USER_DOMAIN}.crt" \
            -clcerts -nokeys \
            -passin pass:"$RANDOM_PASS" 2>&1; then
        log_error "Failed to extract CA certificate."
        exit 1
    fi

    log_info "Extracting CA private key (PEM)..."
    if ! sudo openssl pkcs12 \
            -in "$CERTS_DIR/elastic-stack-ca.p12" \
            -out "$CERTS_DIR/ca_${USER_DOMAIN}.key" \
            -nocerts -nodes \
            -passin pass:"$RANDOM_PASS" 2>&1; then
        log_error "Failed to extract CA private key."
        exit 1
    fi

    # Extract node cert and key
    log_info "Extracting node certificate (PEM)..."
    if ! sudo openssl pkcs12 \
            -in "$CERTS_DIR/$USER_DOMAIN.p12" \
            -out "$CERTS_DIR/$USER_DOMAIN.crt" \
            -clcerts -nokeys \
            -passin pass:"$RANDOM_PASS" 2>&1; then
        log_error "Failed to extract node certificate."
        exit 1
    fi

    log_info "Extracting node private key (PEM)..."
    if ! sudo openssl pkcs12 \
            -in "$CERTS_DIR/$USER_DOMAIN.p12" \
            -out "$CERTS_DIR/$USER_DOMAIN.key" \
            -nocerts -nodes \
            -passin pass:"$RANDOM_PASS" 2>&1; then
        log_error "Failed to extract node private key."
        exit 1
    fi

    log_success "Certificate and key files extracted successfully."
}

# ─────────────────────────────────────────────
#  GENERATE TRUSTSTORE
# ─────────────────────────────────────────────
generate_truststore() {
    log_step "Generating Truststore (truststore.p12)"

    log_info "Importing CA cert into truststore via keytool..."
    log_cmd "keytool -import -alias elastic-ca -file $USER_DOMAIN.crt -keystore truststore.p12"

    if ! keytool -import -alias elastic-ca \
            -file "$CERTS_DIR/$USER_DOMAIN.crt" \
            -keystore "$CERTS_DIR/truststore.p12" \
            -storepass "$RANDOM_PASS" \
            -noprompt 2>&1; then
        log_error "Truststore generation failed."
        exit 1
    fi

    log_success "Truststore created: ${BOLD}$CERTS_DIR/truststore.p12"
}

# ─────────────────────────────────────────────
#  FIX PERMISSIONS
# ─────────────────────────────────────────────
fix_permissions() {
    log_step "Setting File Permissions"

    sudo chown elasticsearch:elasticsearch "$CERTS_DIR"/*
    sudo chmod 640 "$CERTS_DIR"/*.key
    sudo chmod 644 "$CERTS_DIR"/*.crt
    sudo chmod 640 "$CERTS_DIR/truststore.p12"
    sudo chmod 640 "$CERTS_DIR"/*.p12

    log_success "Permissions applied:"
    echo -e "  ${DIM}*.key       → 640 (elasticsearch:elasticsearch)${RESET}"
    echo -e "  ${DIM}*.crt       → 644 (elasticsearch:elasticsearch)${RESET}"
    echo -e "  ${DIM}*.p12       → 640 (elasticsearch:elasticsearch)${RESET}"
    echo -e "  ${DIM}truststore  → 640 (elasticsearch:elasticsearch)${RESET}"
}

# ─────────────────────────────────────────────
#  VERIFY CERTIFICATES
# ─────────────────────────────────────────────
verify_certificates() {
    log_step "Verifying SAN Certificate"

    local cert_file="$CERTS_DIR/$USER_DOMAIN.crt"

    if [ ! -f "$cert_file" ]; then
        log_error "Certificate file not found for verification: ${BOLD}$cert_file"
        exit 1
    fi

    log_info "Verifying Subject Alternative Names in: ${BOLD}$cert_file"
    echo ""

    local san_output
    san_output=$(sudo openssl x509 -in "$cert_file" -noout -text 2>/dev/null \
                  | grep -A1 "Subject Alternative Name" || true)

    if [ -n "$san_output" ]; then
        echo -e "${GREEN}  ✔ SAN Entries Found:${RESET}"
        echo "$san_output" | while IFS= read -r line; do
            echo -e "    ${CYAN}${line}${RESET}"
        done
    else
        log_warn "No SAN entries found in certificate — please check instances.yml."
    fi
}

# ─────────────────────────────────────────────
#  PRINT CERTIFICATE DETAILS (Subject + Validity)
# ─────────────────────────────────────────────
print_certificate_summary() {
    log_step "Certificate Summary"

    local cert_file="$CERTS_DIR/$USER_DOMAIN.crt"
    local ca_cert="$CERTS_DIR/ca_${USER_DOMAIN}.crt"

    echo -e "${BOLD}${WHITE}  ┌─────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${WHITE}  │           Node Certificate Details                  │${RESET}"
    echo -e "${BOLD}${WHITE}  └─────────────────────────────────────────────────────┘${RESET}"

    if [ -f "$cert_file" ]; then
        local subject issuer not_before not_after san

        subject=$(sudo openssl x509 -in "$cert_file" -noout -subject 2>/dev/null \
                  | sed 's/subject=//' | xargs)
        issuer=$(sudo openssl x509 -in "$cert_file" -noout -issuer 2>/dev/null \
                  | sed 's/issuer=//' | xargs)
        not_before=$(sudo openssl x509 -in "$cert_file" -noout -startdate 2>/dev/null \
                  | sed 's/notBefore=//')
        not_after=$(sudo openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null \
                  | sed 's/notAfter=//')
        san=$(sudo openssl x509 -in "$cert_file" -noout -ext subjectAltName 2>/dev/null \
                  | grep -v "Subject Alternative Name" | xargs || echo "N/A")

        echo ""
        echo -e "  ${CYAN}Subject    :${RESET} ${BOLD}$subject${RESET}"
        echo -e "  ${CYAN}Issuer     :${RESET} $issuer"
        echo -e "  ${CYAN}Valid From :${RESET} ${GREEN}$not_before${RESET}"
        echo -e "  ${CYAN}Valid To   :${RESET} ${GREEN}$not_after${RESET}"
        echo -e "  ${CYAN}SANs       :${RESET} ${YELLOW}$san${RESET}"
        echo ""
    else
        log_warn "Certificate file not found: $cert_file"
    fi

    echo -e "${BOLD}${WHITE}  ┌─────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${WHITE}  │              CA Certificate Details                 │${RESET}"
    echo -e "${BOLD}${WHITE}  └─────────────────────────────────────────────────────┘${RESET}"

    if [ -f "$ca_cert" ]; then
        local ca_subject ca_not_before ca_not_after

        ca_subject=$(sudo openssl x509 -in "$ca_cert" -noout -subject 2>/dev/null \
                     | sed 's/subject=//' | xargs)
        ca_not_before=$(sudo openssl x509 -in "$ca_cert" -noout -startdate 2>/dev/null \
                     | sed 's/notBefore=//')
        ca_not_after=$(sudo openssl x509 -in "$ca_cert" -noout -enddate 2>/dev/null \
                     | sed 's/notAfter=//')

        echo ""
        echo -e "  ${CYAN}Subject    :${RESET} ${BOLD}$ca_subject${RESET}"
        echo -e "  ${CYAN}Valid From :${RESET} ${GREEN}$ca_not_before${RESET}"
        echo -e "  ${CYAN}Valid To   :${RESET} ${GREEN}$ca_not_after${RESET}"
        echo ""
    else
        log_warn "CA certificate file not found: $ca_cert"
    fi
}

# ─────────────────────────────────────────────
#  UPDATE ELASTICSEARCH KEYSTORE (AUTOMATED)
# ─────────────────────────────────────────────
update_keystore() {
    log_step "Updating Elasticsearch Keystore"

    # Keys that hold SSL passwords — transport and HTTP layers
    local ssl_keys=(
        xpack.security.http.ssl.keystore.secure_password
        xpack.security.http.ssl.truststore.secure_password
        xpack.security.transport.ssl.keystore.secure_password
        xpack.security.transport.ssl.truststore.secure_password
    )

    # Keys shown in the verification report (read-only — no write)
    local verify_keys=(
        autoconfiguration.password_hash
        keystore.seed
        xpack.security.http.ssl.keystore.secure_password
        xpack.security.http.ssl.truststore.secure_password
        xpack.security.transport.ssl.keystore.secure_password
        xpack.security.transport.ssl.truststore.secure_password
    )

    # ── Step 1: Remove old passwords ──────────────────────────
    echo -e "\n  ${BOLD}${RED}[1/3] Removing old keystore passwords...${RESET}"
    local removed=0 skipped=0

    for key in "${ssl_keys[@]}"; do
        # Check if key exists first — remove fails loudly on missing keys
        if sudo -u elasticsearch "$KEYSTORE_BIN" list 2>/dev/null | grep -q "^${key}$"; then
            log_cmd "elasticsearch-keystore remove $key"
            if sudo -u elasticsearch "$KEYSTORE_BIN" remove "$key" 2>&1; then
                log_success "Removed: ${BOLD}$key"
                removed=$((removed + 1))
            else
                log_warn "Could not remove: ${BOLD}$key${RESET}${YELLOW} — will overwrite with --force"
            fi
        else
            log_info "Key not present (skipping remove): ${BOLD}$key"
            skipped=$((skipped + 1))
        fi
    done
    echo -e "  ${DIM}Removed: $removed  |  Not present (skipped): $skipped${RESET}"

    # ── Step 2: Add new passwords ──────────────────────────────
    echo -e "\n  ${BOLD}${GREEN}[2/3] Adding new keystore passwords...${RESET}"
    local added=0 failed=0

    for key in "${ssl_keys[@]}"; do
        log_cmd "echo '****' | elasticsearch-keystore add --stdin --force $key"
        if echo "$RANDOM_PASS" \
            | sudo -u elasticsearch "$KEYSTORE_BIN" add --stdin --force "$key" 2>&1; then
            log_success "Set: ${BOLD}$key"
            added=$((added + 1))
        else
            log_error "Failed to set: ${BOLD}$key"
            failed=$((failed + 1))
        fi
    done

    if [ "$failed" -gt 0 ]; then
        log_error "$failed keystore password(s) could not be set. Review errors above."
        exit 1
    fi
    echo -e "  ${DIM}Added/Updated: $added${RESET}"

    # ── Step 3: Verify keystore entries ───────────────────────
    echo -e "\n  ${BOLD}${CYAN}[3/3] Verifying keystore entries...${RESET}"
    echo ""
    printf "  %-60s  %s\n" "KEY" "VALUE / STATUS"
    echo -e "  ${DIM}$(printf '%.0s─' {1..75})${RESET}"

    for key in "${verify_keys[@]}"; do
        local value
        if value=$(sudo -u elasticsearch "$KEYSTORE_BIN" show "$key" 2>/dev/null); then
            # Mask actual password values for security — show only first 4 chars
            local masked
            masked="${value:0:4}$(printf '%0.s*' {1..12})"
            printf "  ${CYAN}%-60s${RESET}  ${GREEN}%s${RESET}\n" "$key" "$masked"
        else
            printf "  ${CYAN}%-60s${RESET}  ${YELLOW}%s${RESET}\n" "$key" "(not set)"
        fi
    done
    echo ""
    log_success "Keystore update complete — ${BOLD}${#ssl_keys[@]}${RESET}${GREEN} password(s) applied."
    echo -e "  ${YELLOW}⚠  Restart Elasticsearch to apply the new certificates and passwords:${RESET}"
    echo -e "  ${BOLD}     sudo systemctl restart elasticsearch${RESET}"
    echo ""
}

# ─────────────────────────────────────────────
#  FINAL SUMMARY
# ─────────────────────────────────────────────
print_final_summary() {
    echo ""
    echo -e "${BOLD}${GREEN}"
    echo "  ╔═══════════════════════════════════════════════════════╗"
    echo "  ║   ✅  Certificate Generation Complete!                ║"
    echo "  ╚═══════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "  ${WHITE}Location :${RESET} ${BOLD}$CERTS_DIR${RESET}"
    echo ""
    echo -e "  ${WHITE}Files created:${RESET}"
    echo -e "    ${GREEN}✔${RESET}  elastic-stack-ca.p12   ${DIM}(CA keystore)${RESET}"
    echo -e "    ${GREEN}✔${RESET}  ca_${USER_DOMAIN}.crt    ${DIM}(CA certificate PEM)${RESET}"
    echo -e "    ${GREEN}✔${RESET}  ca_${USER_DOMAIN}.key    ${DIM}(CA private key PEM)${RESET}"
    echo -e "    ${GREEN}✔${RESET}  ${USER_DOMAIN}.p12          ${DIM}(Node keystore)${RESET}"
    echo -e "    ${GREEN}✔${RESET}  ${USER_DOMAIN}.crt          ${DIM}(Node certificate PEM)${RESET}"
    echo -e "    ${GREEN}✔${RESET}  ${USER_DOMAIN}.key          ${DIM}(Node private key PEM)${RESET}"
    echo -e "    ${GREEN}✔${RESET}  truststore.p12          ${DIM}(Truststore)${RESET}"
    echo ""
    echo -e "  ${YELLOW}⚠  Password stored in: ${BOLD}$(pwd)/pass.txt${RESET}"
    echo -e "  ${YELLOW}⚠  Keep this file secure and do not commit it to version control.${RESET}"
    echo ""
}

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
main() {
    print_banner
    check_prerequisites
    backup_elasticsearch_dir      # Full snapshot → /etc/elasticsearch_YYMMDD_hhmmss
    backup_existing_certs          # Granular cert-file backup → certs/backup/<timestamp>/
    prompt_domain
    generate_password
    create_certs_dir
    create_instances_yml
    create_ca
    generate_node_cert
    extract_certs
    generate_truststore
    fix_permissions
    verify_certificates
    print_certificate_summary
    update_keystore                # Automated: remove old → add new → verify
    print_final_summary
}

main "$@"
