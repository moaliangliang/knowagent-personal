/**
 * ZhiXing Notarization Script
 *
 * Runs after electron-builder signs the app. Submits to Apple for notarization
 * using notarytool (recommended over altool).
 *
 * Prerequisites:
 *   1. Apple Distribution cert installed (✅ Y3K9Z836YN)
 *   2. App-specific password saved to Keychain:
 *      security add-generic-password -s "zhixing-notary" -a "YOUR_APPLE_ID_EMAIL" -w "app-specific-password"
 *   3. OR use Apple ID with `APPLE_ID` and `APPLE_APP_SPECIFIC_PASSWORD` env vars
 */

const { notarize } = require("electron-notarize");
const path = require("path");

exports.default = async function (context) {
  const { electronPlatformName, appOutDir } = context;

  // Only notarize on macOS
  if (electronPlatformName !== "darwin") {
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);

  console.log(`📦 Notarizing ${appName}.app ...`);

  const teamId = "Y3K9Z836YN";

  // Try env vars first, then Keychain
  let appleId = process.env.APPLE_ID;
  let appleIdPassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;

  if (!appleId || !appleIdPassword) {
    console.log("⚠️  APPLE_ID or APPLE_APP_SPECIFIC_PASSWORD not set, trying Keychain...");

    const { execSync } = require("child_process");
    try {
      const keychainResult = execSync(
        `security find-generic-password -s "zhixing-notary" -w 2>/dev/null`,
        { encoding: "utf-8", timeout: 5000 }
      ).trim();

      if (keychainResult) {
        // Keychain stores "email:password" or just "password"
        if (keychainResult.includes(":")) {
          const parts = keychainResult.split(":");
          appleId = parts[0];
          appleIdPassword = parts.slice(1).join(":");
        } else {
          // Fallback: assume the Keychain account field has the email
          const accountResult = execSync(
            `security find-generic-password -s "zhixing-notary" | grep "acct" | awk -F'"' '{print $2}'`,
            { encoding: "utf-8", timeout: 5000 }
          ).trim();
          appleId = accountResult || process.env.APPLE_ID;
          appleIdPassword = keychainResult;
        }
        console.log("🔑  Found notary credentials in Keychain");
      }
    } catch {
      console.log("⚠️  Notary credentials not found. Skipping notarization.");
      console.log("   To enable notarization, run:");
      console.log("   security add-generic-password -s 'zhixing-notary' -a 'YOUR@EMAIL.COM' -w 'APP-PASSWORD'");
      return;
    }
  }

  if (!appleId || !appleIdPassword) {
    console.log("⚠️  Apple ID or password missing. Skipping notarization.");
    return;
  }

  try {
    await notarize({
      tool: "notarytool",
      appPath,
      appleId,
      appleIdPassword,
      teamId,
    });
    console.log("✅  Notarization complete!");
  } catch (error) {
    console.error("❌  Notarization failed:", error.message);
    throw error;
  }
};
