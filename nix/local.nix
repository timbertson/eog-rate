{pkgs ? import <nixpkgs> {}}:
with pkgs;
let pythonPackages = python3Packages; in
stdenv.mkDerivation {
	name = "eog-rate";
	src = ./local.tgz;
	buildInputs = [
		gnome3.eog
		(callPackage ../../dumbattr/nix/local.nix {
			inherit pkgs pythonPackages;
		})
		makeWrapper
	];
	installPhase = ''
		mkdir "$out"
		cp -a src "$out/src"
		cp -a xdg "$out/xdg"
		cp -a bin "$out/bin"
		wrapProgram "$out/bin/eog-rate" \
			--set PYTHONPATH "$PYTHONPATH" \
		;
	'';
}

