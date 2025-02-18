with (import <nixpkgs> {});
let
  glibStorePath = lib.getLib glib;

in
stdenv.mkDerivation {
  name = "pygame-env";
  buildInputs = [
    # System requirements.
    glib

    # Python requirements.
    python312Full
    python312Packages.pygame
  ];
  src = null;
  shellHook = ''

    GLIB_PATH="${glibStorePath}/lib"

    LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$GLIB_PATH"

    export LD_LIBRARY_PATH

    # Create and activate virtual environment 
    python -m venv .venv
    source .venv/bin/activate

    pip install pygame
  '';
}
