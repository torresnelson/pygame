with (import <nixpkgs> {});
mkShell {
  name = "pygame-env";
  packages = [
    (python312.withPackages (p: [
      p.pygame
      p.pytest
    ]))
    ruff
  ];
}
