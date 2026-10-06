#!/usr/bin/env bash
#
# Morning Brief Agent — Azure deploy script.
# Idempotent. Reads deploy/secrets.env (gitignored) and provisions:
#   - Resource group + Container Registry + Key Vault + Log Analytics
#   - Azure OpenAI resource (you deploy the model inside it via portal — see below)
#   - Azure Communication Services + Email resource (Azure-managed domain, linked)
#   - Container Apps Environment + Job (cron 6 AM PST + 6 AM PDT UTC slots)
#   - Key Vault secrets + managed identity with get permission
#   - Builds + pushes the Docker image from the repo root
#
# Usage:   ./deploy/deploy.sh
# Prereqs: az login, deploy/secrets.env filled in from secrets-template.env.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/secrets.env"

if [[ ! -f "${SECRETS_FILE}" ]]; then
  echo "Error: ${SECRETS_FILE} not found. Copy secrets-template.env to secrets.env and fill it in." >&2
  exit 1
fi

# shellcheck source=/dev/null
set -a; source "${SECRETS_FILE}"; set +a

# --- Config. Override via env before running. ---
LOCATION="${LOCATION:-eastus}"
RG="${RG:-morning-brief-rg}"
ACR="${ACR:-morningbriefacr}"
KV="${KV:-morning-brief-kv}"
LAW="${LAW:-morning-brief-law}"
CAE="${CAE:-morning-brief-env}"
JOB="${JOB:-morning-brief-job}"
IMAGE_TAG="${IMAGE_TAG:-v1}"
IDENTITY="${IDENTITY:-morning-brief-identity}"
AOAI_NAME="${AOAI_NAME:-morning-brief-ai}"
ACS_NAME="${ACS_NAME:-morning-brief-acs}"
ACS_EMAIL_NAME="${ACS_EMAIL_NAME:-morning-brief-email}"

# Flip to 0 if you've already created the Azure OpenAI / ACS resources yourself.
PROVISION_AOAI="${PROVISION_AOAI:-1}"
PROVISION_ACS="${PROVISION_ACS:-1}"

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
echo ">> Using subscription: ${SUBSCRIPTION_ID}"

echo ">> Resource group: ${RG}"
az group create --name "${RG}" --location "${LOCATION}" -o none

echo ">> Log Analytics workspace"
az monitor log-analytics workspace create -g "${RG}" -n "${LAW}" -o none
LAW_ID="$(az monitor log-analytics workspace show -g "${RG}" -n "${LAW}" --query customerId -o tsv)"
LAW_KEY="$(az monitor log-analytics workspace get-shared-keys -g "${RG}" -n "${LAW}" --query primarySharedKey -o tsv)"

echo ">> Container Registry: ${ACR}"
az acr create -g "${RG}" -n "${ACR}" --sku Basic --admin-enabled true -o none
ACR_LOGIN_SERVER="$(az acr show -n "${ACR}" --query loginServer -o tsv)"

echo ">> Build + push image: ${ACR_LOGIN_SERVER}/morning-brief:${IMAGE_TAG}"
az acr build -r "${ACR}" -t "morning-brief:${IMAGE_TAG}" "${REPO_ROOT}"

echo ">> User-assigned managed identity: ${IDENTITY}"
az identity create -g "${RG}" -n "${IDENTITY}" -o none
IDENTITY_ID="$(az identity show -g "${RG}" -n "${IDENTITY}" --query id -o tsv)"
IDENTITY_PRINCIPAL_ID="$(az identity show -g "${RG}" -n "${IDENTITY}" --query principalId -o tsv)"

echo ">> Granting AcrPull on ${ACR} to ${IDENTITY}"
ACR_ID="$(az acr show -g "${RG}" -n "${ACR}" --query id -o tsv)"
# Idempotent: `az role assignment create` succeeds if the assignment exists.
az role assignment create \
  --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope "${ACR_ID}" -o none 2>/dev/null || true

# --- Azure OpenAI resource (auto-creates the resource; you deploy the model inside it) ---
if [[ "${PROVISION_AOAI}" == "1" ]]; then
  echo ">> Azure OpenAI resource: ${AOAI_NAME}"
  az cognitiveservices account create \
    -g "${RG}" -n "${AOAI_NAME}" \
    --kind OpenAI --sku S0 \
    --location "${LOCATION}" \
    --custom-domain "${AOAI_NAME}" \
    --yes -o none

  # If AZURE_OPENAI_ENDPOINT wasn't provided, derive it from the resource we just made.
  if [[ -z "${AZURE_OPENAI_ENDPOINT:-}" ]]; then
    AZURE_OPENAI_ENDPOINT="$(az cognitiveservices account show -g "${RG}" -n "${AOAI_NAME}" --query properties.endpoint -o tsv)"
    echo "   derived endpoint: ${AZURE_OPENAI_ENDPOINT}"
  fi
  if [[ -z "${AZURE_OPENAI_API_KEY:-}" ]]; then
    AZURE_OPENAI_API_KEY="$(az cognitiveservices account keys list -g "${RG}" -n "${AOAI_NAME}" --query key1 -o tsv)"
    echo "   derived Azure OpenAI API key (masked)"
  fi
fi

# --- Azure Communication Services + Email (Azure-managed domain) ---
if [[ "${PROVISION_ACS}" == "1" ]]; then
  echo ">> Azure Communication Services Email resource: ${ACS_EMAIL_NAME}"
  az communication email create \
    -g "${RG}" -n "${ACS_EMAIL_NAME}" \
    --location "Global" \
    --data-location "United States" \
    -o none

  echo ">> Azure-managed email domain"
  az communication email domain create \
    -g "${RG}" \
    --email-service-name "${ACS_EMAIL_NAME}" \
    --name AzureManagedDomain \
    --location "Global" \
    --domain-management AzureManaged \
    -o none

  EMAIL_DOMAIN_ID="$(az communication email domain show \
    -g "${RG}" --email-service-name "${ACS_EMAIL_NAME}" --name AzureManagedDomain \
    --query id -o tsv)"
  MANAGED_DOMAIN_FQDN="$(az communication email domain show \
    -g "${RG}" --email-service-name "${ACS_EMAIL_NAME}" --name AzureManagedDomain \
    --query fromSenderDomain -o tsv)"

  echo ">> Azure Communication Services resource: ${ACS_NAME} (linked to email domain)"
  az communication create \
    -g "${RG}" -n "${ACS_NAME}" \
    --location "Global" \
    --data-location "United States" \
    --linked-domains "${EMAIL_DOMAIN_ID}" \
    -o none

  if [[ -z "${ACS_CONNECTION_STRING:-}" ]]; then
    ACS_CONNECTION_STRING="$(az communication list-key -g "${RG}" -n "${ACS_NAME}" --query primaryConnectionString -o tsv)"
    echo "   derived ACS connection string (masked)"
  fi
  if [[ -z "${ACS_SENDER_ADDRESS:-}" ]]; then
    ACS_SENDER_ADDRESS="DoNotReply@${MANAGED_DOMAIN_FQDN}"
    echo "   derived sender address: ${ACS_SENDER_ADDRESS}"
  fi
fi

echo ">> Key Vault: ${KV}"
if ! az keyvault show -g "${RG}" -n "${KV}" -o none 2>/dev/null; then
  az keyvault create -g "${RG}" -n "${KV}" --enable-rbac-authorization false -o none
fi
az keyvault set-policy -n "${KV}" --object-id "${IDENTITY_PRINCIPAL_ID}" --secret-permissions get list -o none

echo ">> Storing secrets in Key Vault"
declare -a SECRET_NAMES=(
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_API_KEY
  AZURE_OPENAI_DEPLOYMENT
  AZURE_OPENAI_API_VERSION
  ACS_CONNECTION_STRING
  ACS_SENDER_ADDRESS
  USER_EMAIL
)
for name in "${SECRET_NAMES[@]}"; do
  value="${!name:-}"
  if [[ -n "${value}" ]]; then
    # Key Vault secret names only allow [0-9a-zA-Z-]; translate FOO_BAR → FOO-BAR.
    kv_name="${name//_/-}"
    az keyvault secret set --vault-name "${KV}" --name "${kv_name}" --value "${value}" -o none
    echo "   set ${kv_name}"
  fi
done

echo ">> Container Apps Environment: ${CAE}"
az containerapp env create \
  -g "${RG}" -n "${CAE}" \
  --location "${LOCATION}" \
  --logs-workspace-id "${LAW_ID}" \
  --logs-workspace-key "${LAW_KEY}" \
  -o none

KV_URL="https://${KV}.vault.azure.net/"

# Cron: 14:00 UTC = 6 AM PST (winter). 13:00 UTC = 6 AM PDT (summer).
# Fire at both; Python main.py no-ops the off-hour slot via the LA time gate.
CRON_EXPR="0 13,14 * * *"

echo ">> Container Apps Job: ${JOB}"
az containerapp job create \
  -g "${RG}" -n "${JOB}" \
  --environment "${CAE}" \
  --trigger-type Schedule \
  --cron-expression "${CRON_EXPR}" \
  --replica-timeout 900 \
  --replica-retry-limit 1 \
  --parallelism 1 \
  --replica-completion-count 1 \
  --image "${ACR_LOGIN_SERVER}/morning-brief:${IMAGE_TAG}" \
  --mi-user-assigned "${IDENTITY_ID}" \
  --registry-server "${ACR_LOGIN_SERVER}" \
  --registry-identity "${IDENTITY_ID}" \
  --env-vars \
    "KEY_VAULT_URL=${KV_URL}" \
    "AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT:-gpt-5.4}" \
    "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-2024-10-21}" \
    "BLUESKY_HANDLES=${BLUESKY_HANDLES:-}" \
    "YOUTUBE_CHANNEL_IDS=${YOUTUBE_CHANNEL_IDS:-}" \
    "GITHUB_TRENDING_LANGUAGE=${GITHUB_TRENDING_LANGUAGE:-}" \
  -o none

echo ""
echo "=============================================================="
echo " Deploy complete."
echo ""
echo " === MANUAL STEPS STILL REQUIRED ==="
echo ""
echo " 1. Deploy the GPT-5.4 model in your Azure OpenAI resource:"
echo "      Portal > ${AOAI_NAME} > Model deployments > Create new deployment"
echo "      Model: gpt-5.4, Deployment name: gpt-5.4"
echo "    (or use: az cognitiveservices account deployment create \\"
echo "      -g ${RG} -n ${AOAI_NAME} --deployment-name gpt-5.4 \\"
echo "      --model-name gpt-5.4 --model-version <v> --model-format OpenAI \\"
echo "      --sku-capacity 10 --sku-name Standard)"
echo ""
echo " 2. Set USER_EMAIL in Key Vault if you haven't already (the recipient):"
echo "      az keyvault secret set --vault-name ${KV} --name USER_EMAIL --value 'you@example.com'"
echo ""
echo "    Note: Azure-managed domains are rate-limited. For higher volume,"
echo "    add a custom domain in Portal > ${ACS_EMAIL_NAME} > Domains."
echo ""
echo " === TEST RUN ==="
echo "   az containerapp job start -g ${RG} -n ${JOB}"
echo ""
echo " === LOGS ==="
echo "   az containerapp job execution list -g ${RG} -n ${JOB} -o table"
echo "=============================================================="
