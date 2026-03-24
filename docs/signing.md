# macOS Code Signing and Notarization Setup

This document explains how to configure the five GitHub Actions secrets required
for signed and notarized releases. Once configured, every release tag will
produce a `.dmg` that macOS opens without any Gatekeeper warning.

---

## Prerequisites

- An **Apple Developer account** (paid, $99/year)
- Xcode command-line tools installed locally (`xcode-select --install`)
- Your **Developer ID Application** certificate in your local Keychain

If you don't have a Developer ID Application certificate yet:
1. Open **Xcode → Settings → Accounts**
2. Select your Apple ID → **Manage Certificates**
3. Click **+** → **Developer ID Application**

---

## The Five Secrets

Add each of these in your GitHub repo under
**Settings → Secrets and variables → Actions → New repository secret**.

---

### 1. `APPLE_CERT`

A base64-encoded `.p12` export of your Developer ID Application certificate.

**Steps:**

1. Open **Keychain Access** on your Mac
2. Under **My Certificates**, find **Developer ID Application: Your Name (TEAMID)**
3. Right-click it → **Export**
4. Save as `certificate.p12`, set a strong password (you'll need it for `APPLE_CERT_PASSWORD`)
5. Base64-encode it:
   ```bash
   base64 -i certificate.p12 | pbcopy
   ```
6. Paste the clipboard contents as the secret value

---

### 2. `APPLE_CERT_PASSWORD`

The password you set when exporting the `.p12` in step 4 above.

---

### 3. `APPLE_ID`

Your Apple ID email address (the one associated with your Developer account).

Example: `you@example.com`

---

### 4. `APPLE_ID_PASSWORD`

An **app-specific password** for your Apple ID — not your regular Apple ID password.

**Steps:**

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in → **Sign-In and Security → App-Specific Passwords**
3. Click **+** → label it `LV-Gen CI` → Generate
4. Copy the generated password (format: `xxxx-xxxx-xxxx-xxxx`)
5. Paste as the secret value

---

### 5. `APPLE_TEAM_ID`

Your 10-character Apple Developer Team ID.

**Steps:**

1. Go to [developer.apple.com/account](https://developer.apple.com/account)
2. Scroll to **Membership details**
3. Copy the **Team ID** (looks like `ABC1234DEF`)

---

## Verifying the Setup

After adding all five secrets, push a version tag:

```bash
git tag v0.1.1
git push --tags
```

Watch the **Actions** tab in GitHub. The workflow will:
1. Build the `.app` with PyInstaller
2. Import your certificate into a temporary keychain
3. Sign the `.app` with hardened runtime and entitlements
4. Package it into a `.dmg`
5. Submit the `.dmg` to Apple for notarization (takes ~1–5 minutes)
6. Staple the notarization ticket to the `.dmg`
7. Attach the signed, notarized `.dmg` to the GitHub Release

Users downloading the `.dmg` will see no Gatekeeper warning — the app opens normally on first launch.

---

## Troubleshooting

**`errSecInternalComponent` during codesign**
The keychain is locked. This shouldn't happen in CI but if it does, check that
the `security unlock-keychain` step ran successfully.

**Notarization rejected: `APPLE_ID_PASSWORD` invalid**
App-specific passwords expire or can be revoked. Generate a new one at
appleid.apple.com and update the secret.

**Notarization rejected: hardened runtime issues**
Apple requires the hardened runtime (`--options runtime`) and specific
entitlements for Python apps. The `entitlements.plist` in this repo already
includes the required `allow-unsigned-executable-memory` and
`disable-library-validation` entitlements.

**`stapler` fails after notarization**
Stapling requires network access to retrieve the ticket. The GitHub Actions
runner has internet access so this should not be an issue in CI.
