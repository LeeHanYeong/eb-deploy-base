#!/usr/bin/env python
import subprocess


def run(cmd, **kwargs):
    subprocess.run(cmd, shell=True, **kwargs)


DOCKERHUB_TAG = 'azelf/eb-deploy-ci'

if __name__ == '__main__':
    run(f'docker build -t {DOCKERHUB_TAG} -f Dockerfile.ci .')
    run(f'docker push {DOCKERHUB_TAG}')
