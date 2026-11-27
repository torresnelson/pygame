# Rust toolchain and the native libraries bevy needs on NixOS.
#
#   cd rust && nix-shell
#   cargo run -p tetris
with (import <nixpkgs> {});
let
  runtimeLibs = [
    alsa-lib
    udev
    vulkan-loader
    libxkbcommon
    wayland
    libx11
    libxcursor
    libxi
    libxrandr
  ];
in
mkShell {
  name = "pygame-sandbox-rust";
  packages = [
    rustc
    cargo
    rustfmt
    clippy
    lld
    pkg-config
    wasm-bindgen-cli
    binaryen
  ] ++ runtimeLibs;
  # winit and wgpu load these at runtime with dlopen.
  LD_LIBRARY_PATH = lib.makeLibraryPath runtimeLibs;
}
