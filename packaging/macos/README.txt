FaceLES for macOS
=================

Build on a Mac:

  ./scripts/build_macos.sh

That creates:

  dist/FaceLES.app
  dist/FaceLES-macOS.zip

Employees unzip (if needed), drag FaceLES.app to Applications, then open it.
The first launch of an unsigned app: right-click the app → Open.

Camera permission is requested the first time (NSCameraUsageDescription).

Logs and enrolled face:
  ~/Library/Application Support/FaceLES/

To notarize for other people's Macs you need an Apple Developer account
and codesign + notarytool. Without that, Gatekeeper will warn.
