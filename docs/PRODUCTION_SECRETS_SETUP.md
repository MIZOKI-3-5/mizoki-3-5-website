# Production secrets — one-time setup

The `mizoki-website` Cloud Run service reads two secrets at runtime via Secret Manager. The sole human-gated production workflow, `deploy-homepage.yml`, attaches them with merge-preserving `--update-secrets`; `# MIZ OKI 3.5/cloudbuild.yaml` only builds and pushes an image and does not deploy Cloud Run.

| Secret name | Maps to env var | What it does |
|:------------|:----------------|:-------------|
| `mizoki-website-secret-key` | `SECRET_KEY` | Flask session signing key. Pinning it means sessions survive container restarts. |
| `mizoki-website-demo-users` | `MIZOKI_DEMO_USERS_JSON` | `{email: password_hash}` map for `/admin/login`. Values are **werkzeug `pbkdf2:sha256:600000` hashes**, not plaintext passwords — `app.py` verifies with `check_password_hash` and never stores a raw password past process boot (MIZ-SEC 2026-08-26). |

## Step 1 — generate strong values locally

Run this on your laptop (or in any throwaway shell). Output is **not** committed; copy it into `1Password` / `Bitwarden` / wherever you keep ops creds, then proceed to step 2. **Save the plaintext passwords somewhere an operator can retrieve them (e.g. the password manager entry) — only the hash goes into the secret, and a hash cannot be reversed back into a password to hand to a new admin.**

```bash
python3 - <<'PY'
import secrets, string, json
from werkzeug.security import generate_password_hash

sk = secrets.token_hex(32)
alphabet = (string.ascii_letters.replace('l','').replace('I','').replace('O','')
            + string.digits.replace('0','').replace('1','') + '!@#%^&*-_=+')
plaintext = {
    'admin@mizoki3.com':        ''.join(secrets.choice(alphabet) for _ in range(24)),
    'ceo@mediaintelligence.ai': ''.join(secrets.choice(alphabet) for _ in range(24)),
}
# Same method app.py uses (_DEMO_PASSWORD_HASH_METHOD) — PBKDF2 rather than
# werkzeug's scrypt default, since scrypt needs an OpenSSL build with
# hashlib.scrypt, which is not universally available.
hashed = {email: generate_password_hash(pw, method="pbkdf2:sha256:600000")
          for email, pw in plaintext.items()}
print('SECRET_KEY:               ', sk)
print('Plaintext (save to password manager, NOT to the secret):')
print(json.dumps(plaintext, indent=2))
print('MIZOKI_DEMO_USERS_JSON:   ', json.dumps(hashed))
PY
```

Note: `app.py` also accepts a bare plaintext value in `MIZOKI_DEMO_USERS_JSON` for
backward compatibility — it is hashed in memory at boot before ever being
compared — but a value that has not been rotated to a hash still means the
plaintext password sits in the Secret Manager version's history. Rotate to a
real hash as above at the next opportunity; new secrets should always be
created hashed.

## Step 2 — push the values into Secret Manager

Replace `<SECRET_KEY>` and `<USERS_JSON>` with what step 1 printed.

```bash
PROJECT=spry-bus-425315-p6

# Create the secrets (idempotent: ignore "already exists")
gcloud secrets create mizoki-website-secret-key  --project="$PROJECT" --replication-policy=automatic 2>/dev/null || true
gcloud secrets create mizoki-website-demo-users --project="$PROJECT" --replication-policy=automatic 2>/dev/null || true

# Add a version to each. Use printf (not echo) so no trailing newline is included.
printf %s '<SECRET_KEY>' | \
  gcloud secrets versions add mizoki-website-secret-key  --project="$PROJECT" --data-file=-

printf %s '<USERS_JSON>' | \
  gcloud secrets versions add mizoki-website-demo-users --project="$PROJECT" --data-file=-
```

## Step 3 — grant the Cloud Run runtime SA read access

Cloud Run uses the default Compute Engine service account unless overridden. Grant it `secretAccessor` on each secret.

```bash
PROJECT=spry-bus-425315-p6
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com

for s in mizoki-website-secret-key mizoki-website-demo-users; do
  gcloud secrets add-iam-policy-binding "$s" \
    --project="$PROJECT" \
    --member="serviceAccount:${SA}" \
    --role=roles/secretmanager.secretAccessor
done
```

## Step 4 — protect the deployment control plane (required before any next dispatch)

The workflow source is deliberately fail-closed until all of the controls below
exist. A missing environment, unprotected `main`, a repository-level JSON key,
or an implicitly created environment is not an acceptable fallback.

### GitHub repository controls

1. Protect `main` with a branch rule or ruleset that requires pull requests,
   at least one non-author approval, dismissal of stale approvals, resolved
   conversations, and the repository's required checks. Apply the rule to
   administrators, block force pushes and deletion, and give GitHub Actions no
   bypass. The direct-to-`main` AI merge lanes must remain blocked until they
   are redesigned to execute only default-branch-controlled code.
2. Add a second named, trusted collaborator before requiring CODEOWNER review
   on owner-authored pull requests. `@mediaintelligence` is the valid current
   owner; the old organization-team handle was invalid for this personal repo.
3. Pre-create the `homepage-production` environment. Restrict its deployment
   branch to the exact selected branch `main`; do not choose **Protected
   branches only** while no effective branch protection is present. If the
   repository plan exposes required environment reviewers, require a reviewer
   and prevent self-review. Private-repository reviewer gates are plan-limited,
   so the protected-branch rule and Workload Identity Federation conditions
   remain mandatory.
4. Add these variables to `homepage-production`:

   - `HOMEPAGE_PRODUCTION_ENVIRONMENT_GUARD=configured-v1`
   - `HOMEPAGE_PRODUCTION_WIF_PROVIDER=projects/<number>/locations/global/workloadIdentityPools/<pool>/providers/<provider>`
   - `HOMEPAGE_PRODUCTION_SERVICE_ACCOUNT=<dedicated-deployer>@spry-bus-425315-p6.iam.gserviceaccount.com`

5. Add separate repository variables for read-only diagnosis:

   - `HOMEPAGE_DIAGNOSTIC_WIF_PROVIDER=projects/<number>/locations/global/workloadIdentityPools/<pool>/providers/<provider>`
   - `HOMEPAGE_DIAGNOSTIC_SERVICE_ACCOUNT=<dedicated-viewer>@spry-bus-425315-p6.iam.gserviceaccount.com`

### Google Cloud identity controls

Use keyless GitHub OIDC Workload Identity Federation. The production provider
must trust only repository ID `1008435662`, `refs/heads/main`,
`workflow_dispatch`, actor ID `163805125`, the exact
`deploy-homepage.yml@refs/heads/main` workflow identity, and environment
`homepage-production`. Give its dedicated service account only the permissions
needed to submit/inspect this build, stage and route this Cloud Run service, and
act as the existing runtime service account. Do not grant project IAM admin.

Use a different provider/service account for `fix-homepage-deploy.yml`, bound to
that exact workflow on `main`, with only Cloud Build Viewer and Cloud Run Viewer
access. It must not be able to submit builds, create revisions, or update
traffic.

Inspect both providers and service-account IAM policies read-only, then verify
the diagnostic viewer identity through its non-mutating workflow. Disable every
service-account key formerly stored in `GCP_SA_KEY` and remove that repository
secret **before** any production dispatch. Do not keep the old key as a fallback
while testing the production identity: the first specifically approved
production attempt must use WIF and fail closed if federation is wrong.
Historical workflow runs retain their old workflow definitions; revoking the
old key is what makes those re-runs harmless. Keep a short observation window,
then delete the disabled key under the normal credential-rotation procedure.

These settings are administrator operations and are not created by merging the
source patch. Do not dispatch production until all of them are independently
confirmed.

## Step 5 — deploy through the governed workflow

Do not run `gcloud builds submit` expecting it to deploy the service. The Cloud Build file is build-and-push only.

From GitHub Actions, start a new **Deploy MIZ OKI 3.5 Homepage** dispatch,
select `main`, enter the exact 40-character `main` commit in `approved_sha`,
provide the deployment reason, and type the exact `APPROVED` input. Only the
repository owner's GitHub actor ID is accepted. Do not use **Re-run jobs** for a
production attempt. Every new attempt requires a fresh dispatch and approval.

1. proves the selected ref is `refs/heads/main`;
2. runs the site and `/intent` gates, including the hash-locked docs build dependency;
3. builds a commit-tagged image and takes its immutable digest directly from that exact successful Cloud Build result;
4. immediately snapshots the stable 100%-serving revision and every normalized env/secret binding;
5. stages a no-traffic revision with merge-preserving env/secret updates;
6. proves the tagged candidate is ready with the approved digest and preserved bindings while traffic remains on the recorded old revision;
7. checks `/intent` and the representative existing routes through the zero-percent candidate URL;
8. routes 100% to that exact verified revision;
9. proves the live image, bindings, latest-ready state, and traffic are exact;
10. repeats the focused checks from the service URL and `mizoki3.com`;
11. removes the temporary candidate tag, including on a failed attempted rollout;
12. on success, re-verifies final image, binding, traffic, and tag-absence state.

The legacy `fix-homepage-deploy.yml` file now appears as **Diagnose Homepage Deployment (read-only)**. It can compare a main-ancestor commit and exact Cloud Build result with the current live image, configuration, and routes. It cannot build, deploy, update traffic, or change Cloud Run. It is not an approval or recovery bypass.

## Step 6 — verify

The workflow now hard-fails if the route/configuration contract fails. For a manual credential check after a green deployment:

```bash
# /admin/login should render the form
curl -sI https://mizoki3.com/admin/login | head -1
#   HTTP/2 200

# /admin without a session should 302 to /admin/login
curl -sI https://mizoki3.com/admin | head -2
#   HTTP/2 302
#   location: /admin/login
```

Then sign in with the credentials from step 1. Do not put those credentials in an Actions input, issue, PR, or workflow log.

## Rotating

The current service references `:latest`. Secret-backed environment variables are resolved when an instance starts, not only when a new revision is deployed. Adding a new secret version can therefore affect newly started instances without a homepage dispatch and can temporarily mix values across instances. Treat creating or enabling a new version as a production change; for `SECRET_KEY`, an uncoordinated change can also split session-signing state.

Prepare rotations as a separately reviewed operation. The safest follow-up is to migrate the workflow and guard together to an explicitly approved numeric secret version, verify the new revision, and only then retire the old version. Do not add a new `latest` version on the assumption that it will wait for the next deploy.

When that reviewed rotation is ready, add the version without a trailing newline:

```bash
printf %s '<NEW_VALUE>' | \
  gcloud secrets versions add mizoki-website-secret-key --project=spry-bus-425315-p6 --data-file=-
```

Do not apply a one-off `gcloud run services update`; production changes use the reviewed canonical workflow. Rotating `SECRET_KEY` invalidates all existing admin sessions (everyone has to sign in again). Rotating `MIZOKI_DEMO_USERS_JSON` does **not** invalidate existing sessions — old session cookies stay valid until they expire (8 hours) or the user signs out.

## Gating the API surface

`MIZOKI_REQUIRE_AUTH_FOR_APIS` is currently a workflow-managed value set to `false` for the public site-level chat demo. Changing it is a production-policy decision and must be made in the reviewed deployment workflow; a one-off revision update would be restored to `false` by the next approved homepage deployment.

`/api/health` always stays public for monitoring. When the reviewed value is `true`, other routes under `/api/mcp/*` and `/api/boss/*` return `401 {"error":"Authentication required"}` to unauthenticated callers.
