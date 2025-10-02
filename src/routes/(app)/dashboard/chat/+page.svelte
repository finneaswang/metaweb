<script lang="ts">
	import { onMount } from "svelte";
	import { user } from "$lib/stores";
	import { goto } from "$app/navigation";
	import Chat from "$lib/components/chat/Chat.svelte";
</script>

<div class="h-full">
	<Chat />
</div>
