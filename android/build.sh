#!/usr/bin/env bash
# MorHesap APK derleme betiği (Gradle gerektirmez).
# Gerekenler (Debian/Ubuntu): sudo apt install default-jdk aapt apksigner zipalign dalvik-exchange libandroid-23-java
set -euo pipefail
cd "$(dirname "$0")"
ANDROID_JAR="${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}"
KEYSTORE="${KEYSTORE:-morhesap.keystore}"
KEYPASS="${KEYPASS:-morhesap123}"
OUT=build
rm -rf "$OUT" && mkdir -p "$OUT/gen" "$OUT/classes" "$OUT/dex"

aapt package -f -m -J "$OUT/gen" -M AndroidManifest.xml -S res -I "$ANDROID_JAR"
javac -nowarn --release 8 -cp "$ANDROID_JAR" -d "$OUT/classes" \
    $(find src "$OUT/gen" -name '*.java')
dalvik-exchange --dex --output="$OUT/dex/classes.dex" "$OUT/classes"
aapt package -f -0 arsc -M AndroidManifest.xml -S res -A assets -I "$ANDROID_JAR" -F "$OUT/unsigned.apk"
(cd "$OUT/dex" && aapt add ../unsigned.apk classes.dex >/dev/null)
zipalign -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"

if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair -keystore "$KEYSTORE" -storepass "$KEYPASS" -keypass "$KEYPASS" \
        -alias morhesap -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=MorHesap"
fi
apksigner sign --ks "$KEYSTORE" --ks-pass "pass:$KEYPASS" --key-pass "pass:$KEYPASS" \
    --out "$OUT/MorHesap.apk" "$OUT/aligned.apk"
apksigner verify "$OUT/MorHesap.apk"
echo "Hazır: $OUT/MorHesap.apk"
