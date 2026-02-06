# Building Armagetron Advanced on macOS

## Prerequisites

Install dependencies via Homebrew:

```bash
brew install autoconf automake libtool boost sdl2 sdl2_image sdl2_mixer \
             libxml2 protobuf ftgl freetype pkg-config libpng
```

For app packaging, also install:

```bash
brew install dylibbundler create-dmg
```

## A) Basic Development Build

This builds and runs from the source tree without installing.

```bash
# Generate build system (only needed once or after changing configure.ac)
autoreconf -i

# 
./bootstrap.sh

# Configure with boost paths
./configure --with-boost=/opt/homebrew/opt/boost CPPFLAGS="-I/opt/homebrew/opt/boost/include"

# Build
make -j$(sysctl -n hw.ncpu)

# Run the game
make run

./src/armagetronad_main
```

### Rebuilding After Code Changes

```bash
make -j8
./src/armagetronad_main
```

### Clean Build

```bash
make clean
make -j8
```

### Full Clean (removes all generated files)

```bash
make distclean
# Then run configure and make again
```

## B) macOS App Package (.app bundle + DMG)

This creates a standalone `Armagetronad Advanced.app` and distributable DMG.

### Build from Scratch

```bash
# Create a separate build directory
rm -rf build-bundle

make distclean

mkdir build-bundle

# Generate version file (required before configure)
sh batch/make/version --verbose . | awk '{ print "#define TRUE_ARMAGETRONAD_" $1 " " substr( $0, index( $0, $2 ) ) }' > src/tTrueVersion.h

cd build-bundle

# Configure for bundle (pass boost paths)
../desktop/os-x/configure_for_bundle.sh --with-boost=/opt/homebrew/opt/boost CPPFLAGS="-I/opt/homebrew/opt/boost/include"

# Build
make -j8

# Create app bundle and DMG
chmod +x desktop/os-x/build_bundle.sh
./desktop/os-x/build_bundle.sh
```

### Output Files

After `build_bundle.sh` completes:

- **App bundle**: `build-bundle/Armagetronad Advanced.app`
- **DMG installer**: `build-bundle/armagetronad-*.dmg`
- **ZIP archive**: `build-bundle/armagetronad-client-*.macOS.zip`

### Run Without Installing

```bash
open "build-bundle/Armagetronad Advanced.app"
```

Or directly:

```bash
"build-bundle/Armagetronad Advanced.app/Contents/MacOS/Armagetronad Advanced"
```

### Rebuild After Code Changes

```bash
cd build-bundle
make -j8
./desktop/os-x/build_bundle.sh
```

## Troubleshooting

### Boost headers not found

```
fatal error: 'boost/tuple/tuple.hpp' file not found
```

Solution: Pass boost paths to configure:

```bash
CPPFLAGS="-I/opt/homebrew/opt/boost/include" ./configure --with-boost=/opt/homebrew/opt/boost
```

### tTrueVersion.h not found

```
fatal error: 'tTrueVersion.h' file not found
```

Solution: Configure didn't complete. Clean and reconfigure:

```bash
rm -rf build-bundle && mkdir build-bundle && cd build-bundle
CPPFLAGS="-I/opt/homebrew/opt/boost/include" ../desktop/os-x/configure_for_bundle.sh --with-boost=/opt/homebrew/opt/boost
```

### Source directory already configured

```
configure: error: source directory already configured
```

Solution: Run `make distclean` from the project root before reconfiguring.

### Homebrew permission errors

```
/opt/homebrew/Cellar is not writable
```

Solution:

```bash
sudo chown -R $(whoami) /opt/homebrew
```

## Publishing a Release

### Prerequisites

Install GitHub CLI (if not already installed):

```bash
brew install gh
gh auth login
```

### Method 1: Using GitHub CLI (Recommended)

```bash
# Tag the release
git tag v0.4.0-mining-truck
git push origin v0.4.0-mining-truck

# Create release with DMG installer
gh release create v0.4.0-mining-truck \
  --title "Mining Truck Edition v0.4.0" \
  --notes "Release notes here." \
  "build-bundle/armagetronad-*.dmg"

# Or include all artifacts (.app, DMG, and ZIP)
gh release create v0.4.0-mining-truck \
  --title "Mining Truck Edition v0.4.0" \
  --notes "Release notes here." \
  "build-bundle/Armagetron Advanced.app" \
  "build-bundle/armagetronad-*.dmg" \
  "build-bundle/armagetronad-client-*.macOS.zip"
```

### Method 2: Using GitHub Web UI

1. Push the tag first:
   ```bash
   git tag v0.4.0-mining-truck
   git push origin v0.4.0-mining-truck
   ```

2. Go to your repository on GitHub → **Releases** → **Draft a new release**

3. Select the tag `v0.4.0-mining-truck`

4. Fill in:
   - **Title**: "Mining Truck Edition v0.4.0"
   - **Description**: Your release notes

5. Drag and drop files from `build-bundle/`:
   - `armagetronad-*.dmg` (DMG installer - recommended for macOS users)
   - `Armagetron Advanced.app` (optional - raw app bundle)
   - `armagetronad-client-*.macOS.zip` (optional - ZIP archive)

6. Click **Publish release**
