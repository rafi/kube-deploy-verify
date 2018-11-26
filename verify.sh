#!/usr/bin/env bash

main() {
	local name="${1}"
	local output
	local state
	local previous_state
	local failed=0
	local success=0
	local failed_times=0
	local success_times=0

	if [[ $# != 1 ]]; then
		echo "usage: $(basename "$0") <deployment>" >&2
		exit 1
	fi

	# Loop for 60 seconds or until failed or successful flags are raised.
	while [ ${SECONDS} -lt 60 ] && [ $failed = 0 ] && [ $success = 0 ]; do
		output=$(kubectl get pod -l app="${name}" -o json | jq '[.items[] | select(.metadata.deletionTimestamp == null)]')
		current_ready=$(echo "${output}" | jq -r '.[] | "\(.status.containerStatuses[].ready)"' | sort | uniq)
		current_state=$(echo "${output}" | jq -r '.[] | "\(.status.containerStatuses[].state | keys | join(","))"' | sort | uniq)

		state=$(echo "${output}" | jq -r '.[]
			| "\(.metadata.name): \(.status.containerStatuses[].state | keys | join(",")) (\(.status.containerStatuses[].state[].reason)) (\(.status.containerStatuses[].ready))"')

		if [ "$current_state" = "running" ] && [ "$current_ready" = "true" ]; then
			((success_times++))
			[ $success_times -gt 10 ] && success=1
		else
			success_times=0
		fi

		if [[ "$current_state" == *terminated* ]] || [[ "$current_state" == *waiting* ]]; then
			((failed_times++))
			[ $failed_times -gt 5 ] && failed=1
		else
			failed_times=0
		fi

		if [ "$state" != "$previous_state" ]; then
			clear
			echo "${state}"
			previous_state="${state}"
		fi
		sleep .5
	done

	if [ $failed -eq 1 ]; then
		echo "${output}" | jq '.[] | {status: .status.containerStatuses[].state}'
		echo -e "\\nDeployment pods aren't able to run, aborting."
		exit 1
	elif [ $success -eq 1 ]; then
		echo -e 'Deployment pods are running, hooray!'
		exit 0
	fi
}

main "$@"
