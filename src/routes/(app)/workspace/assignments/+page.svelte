<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let assignments = [];
	let loading = true;
	let filter = 'all'; // all, draft, published, closed

	// Fetch assignments from API
	const fetchAssignments = async () => {
		loading = true;
		try {
			const res = await fetch(`/api/metaweb/assignments?status=${filter === 'all' ? '' : filter}`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error('Failed to fetch assignments');
			}

			assignments = await res.json();
		} catch (error) {
			console.error('Error fetching assignments:', error);
			toast.error($i18n.t('Failed to load assignments'));
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (!$user) {
			goto('/');
			return;
		}


		await fetchAssignments();
	});

	// Format date
	const formatDate = (dateString) => {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleDateString('zh-CN', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit'
		});
	};

	// Get status badge color
	const getStatusColor = (status) => {
		const colors = {
			draft: 'bg-gray-500',
			published: 'bg-green-500',
			closed: 'bg-red-500'
		};
		return colors[status] || 'bg-gray-500';
	};

	// Navigate to create assignment page
	const createAssignment = () => {
		goto('/workspace/assignments/create');
	};

	// Navigate to assignment detail
	const viewAssignment = (id) => {
		goto(`/workspace/assignments/${id}`);
	};
</script>

<svelte:head>
	<title>{$i18n.t('Assignments')} | {$i18n.t('Open WebUI')}</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="p-6 border-b border-gray-100 dark:border-gray-800">
		<div class="flex justify-between items-center">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Assignments')}
				</h1>
				<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
					{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
						{$i18n.t('Manage assignments and review submissions')}
					{:else}
						{$i18n.t('View and submit your assignments')}
					{/if}
				</p>
			</div>

			{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
				<button
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center gap-2"
					on:click={createAssignment}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="w-5 h-5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M12 4.5v15m7.5-7.5h-15"
						/>
					</svg>
					{$i18n.t('Create Assignment')}
				</button>
			{/if}
		</div>

		<!-- Filter Tabs -->
		<div class="flex gap-2 mt-4">
			<button
				class="px-4 py-2 rounded-lg transition {filter === 'all'
					? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
					: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
				on:click={() => {
					filter = 'all';
					fetchAssignments();
				}}
			>
				{$i18n.t('All')}
			</button>
			{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
				<button
					class="px-4 py-2 rounded-lg transition {filter === 'draft'
						? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
						: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
					on:click={() => {
						filter = 'draft';
						fetchAssignments();
					}}
				>
					{$i18n.t('Draft')}
				</button>
			{/if}
			<button
				class="px-4 py-2 rounded-lg transition {filter === 'published'
					? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
					: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
				on:click={() => {
					filter = 'published';
					fetchAssignments();
				}}
			>
				{$i18n.t('Published')}
			</button>
			<button
				class="px-4 py-2 rounded-lg transition {filter === 'closed'
					? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
					: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
				on:click={() => {
					filter = 'closed';
					fetchAssignments();
				}}
			>
				{$i18n.t('Closed')}
			</button>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
			</div>
		{:else if assignments.length === 0}
			<div class="flex flex-col items-center justify-center h-64 text-gray-500">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-16 h-16 mb-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
					/>
				</svg>
				<p class="text-lg">{$i18n.t('No assignments found')}</p>
				{#if $user?.role === 'teacher' || $user?.role === 'leader' || $user?.role === 'admin'}
					<button
						class="mt-4 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
						on:click={createAssignment}
					>
						{$i18n.t('Create your first assignment')}
					</button>
				{/if}
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each assignments as assignment}
					<div
						class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition cursor-pointer"
						on:click={() => viewAssignment(assignment.id)}
						on:keydown={(e) => {
							if (e.key === 'Enter') viewAssignment(assignment.id);
						}}
						role="button"
						tabindex="0"
					>
						<div class="p-4">
							<!-- Header -->
							<div class="flex justify-between items-start mb-3">
								<h3
									class="text-lg font-semibold text-gray-900 dark:text-white line-clamp-2"
								>
									{assignment.title}
								</h3>
								<span
									class="px-2 py-1 text-xs text-white rounded-full {getStatusColor(
										assignment.status
									)}"
								>
									{$i18n.t(assignment.status)}
								</span>
							</div>

							<!-- Description -->
							<p class="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
								{assignment.description || $i18n.t('No description')}
							</p>

							<!-- Meta Info -->
							<div class="flex flex-col gap-2 text-sm text-gray-500 dark:text-gray-400">
								<div class="flex items-center gap-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
										/>
									</svg>
									<span>{assignment.subject || $i18n.t('General')}</span>
								</div>

								<div class="flex items-center gap-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"
										/>
									</svg>
									<span
										>{$i18n.t('Due')}: {formatDate(assignment.due_date)}</span
									>
								</div>

								<div class="flex items-center gap-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"
										/>
									</svg>
									<span>{assignment.total_points} {$i18n.t('points')}</span>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
