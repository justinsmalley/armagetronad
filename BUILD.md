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
mkdir build-bundle
cd build-bundle

# Configure for bundle (pass boost paths)
CPPFLAGS="-I/opt/homebrew/opt/boost/include" \
    ../desktop/os-x/configure_for_bundle.sh --with-boost=/opt/homebrew/opt/boost

# Build
make -j8

# Create app bundle and DMG
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

```bash
git tag v0.4.0-mining-truck
git push origin v0.4.0-mining-truck

gh release create v0.4.0-mining-truck \
  --title "Mining Truck Edition v0.4.0" \
  --notes "Release notes here." \
  "build-bundle/armagetronad-*.dmg"
```
