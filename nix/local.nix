{pkgs ? import <nixpkgs> {}}:
with pkgs;
let pythonPackages = python3Packages; in
pkgs.stdenv.mkDerivation {
	name = "eog-rate";
	src = ./local.tgz;
	buildInputs = [
		pkgs.gnome3.eog
		pkgs.makeWrapper
		(pkgs.callPackage ../../dumbattr/nix/local.nix {
			inherit pkgs pythonPackages;
		})
	];
	shellHook = ''
		export PATH="${pkgs.gnome3.eog}/bin:$PATH";
		export PYTHONPATH="${pythonPackages.pygobject3}/lib/${pythonPackages.python.libPrefix}/site-packages:$PYTHONPATH"
	'';
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

