<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, config, user } from '$lib/stores';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		// No feature flag check for assignments - always allow if authenticated
		if (!$user) {
			goto('/auth');
			return;
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Assignments')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="w-full flex-1 h-full flex {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ' '}"
		id="main-content"
	>
		<slot />
	</div>
{/if}





