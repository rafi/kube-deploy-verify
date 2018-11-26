import sys
import time
import signal
from kubernetes import client, config, watch

TIMEOUT_SECONDS = 60 * 5
POD_PASS_COUNT = 20

config.load_kube_config()
CoreV1Api = client.CoreV1Api()
AppsV1Api = client.AppsV1Api()


def signal_handler(signum, frame):
    print("timeout after {} seconds".format(TIMEOUT_SECONDS))
    sys.exit(1)


def get_deploy(name, namespace):
    try:
        return AppsV1Api.read_namespaced_deployment_status(
            name, namespace, pretty=True)
    except client.rest.ApiException as e:
        print(e)
        return False


def get_pods(name, namespace,label):
    try:
        return CoreV1Api.list_namespaced_pod(
            namespace,
            label_selector="app={}".format(label),
        )
    except client.rest.ApiException as e:
        print(e)
        return False


def verify_pods(name, namespace,label):
    running = failed = 0
    while running < POD_PASS_COUNT and failed < POD_PASS_COUNT:
        time.sleep(2)
        pods = get_pods(name, namespace,label)
        if not pods:
            raise Exception('cannot find deployment pods')
        for pod in pods.items:
            if pod.metadata.deletion_timestamp:
                continue
            for status in pod.status.container_statuses:
                ready = status.ready
                running = (running+1) if status.state.running and ready else 0
                failed = (failed+1) if status.state.terminated else 0
                if status.state.waiting:
                    running = failed = 0
            print('Waiting for pod {}... state: {}'.format(
                pod.metadata.name,
                'failed' if failed else 'running' if running else ''
            ))

    return running > failed


def verify_generation(name, namespace):
    deploy = get_deploy(name, namespace)
    if not deploy:
        raise Exception('cannot find deployment')

    observed_gen = -1
    gen = deploy.metadata.generation
    print('waiting for specified generation {} to be observed'.format(gen))
    while observed_gen < gen:
        time.sleep(2)
        deploy = get_deploy(name, namespace)
        observed_gen = deploy.status.observed_generation
    print('specified generation observed.')


def verify_replicaset(name, namespace):
    deploy = get_deploy(name, namespace)
    if not deploy:
        raise Exception('cannot find deployment')
    replicas_count = deploy.spec.replicas
    print('specified replicas: {}'.format(replicas_count))

    available = -1
    while available != replicas_count:
        time.sleep(2)
        deploy = get_deploy(name, namespace)
        available = deploy.status.available_replicas
        print('available replicas: {}'.format(available))


def main():
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(TIMEOUT_SECONDS)

    if len(sys.argv) < 2:
        print('usage: verify.py <deployment> [app-label] [namespace]')
        sys.exit(1)
    else:
        deploy_name = sys.argv[1]
        label = sys.argv[2] if len(sys.argv) > 2 else deploy_name
        namespace = sys.argv[3] if len(sys.argv) > 3 else 'default'

    try:
        verify_generation(deploy_name, namespace)
        verify_replicaset(deploy_name, namespace)
        print('deployment complete.')
        verify_pods(deploy_name, namespace,label)
        print('deployment pods are running, hooray!')
    except KeyboardInterrupt as e:
        print('aborting...')
    except Exception as e:
        print(e)
        print('aborting...')
        sys.exit(2)


if __name__ == '__main__':
    main()
