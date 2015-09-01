from setuptools.command.install import install
from subprocess import call

class CustomInstall(install):

    def run(self):
        install.run(self)
        #print("running custom install steps...")
	#implement custom install steps if needed
