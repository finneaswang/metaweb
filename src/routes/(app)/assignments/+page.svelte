<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { 
		getAssignments, 
		createNewAssignment, 
		submitAssignment as submitAssignmentAPI,
		deleteAssignmentById
	} from '$lib/apis/assignments';

	const i18n = getContext('i18n');

	let assignments = [];
	let newAssignment = {
		title: '',
		description: '',
		due_date: ''
	};
	let loading = true;
	let submitting = false;
	let creating = false;

	onMount(async () => {
		if (!$user) {
			goto('/auth');
			return;
		}
		await loadAssignments();
	});

	const loadAssignments = async () => {
		try {
			loading = true;
			const token = localStorage.getItem('token');
			const result = await getAssignments(token);
			if (result) {
				assignments = result;
			}
		} catch (error) {
			console.error('Failed to load assignments:', error);
		} finally {
			loading = false;
		}
	};

	const submitAssignment = async (assignmentId: string) => {
		try {
			submitting = true;
			const token = localStorage.getItem('token');
			const result = await submitAssignmentAPI(token, assignmentId);
			
			if (result) {
				// Refresh assignments list
				await loadAssignments();
				alert($i18n.t('Assignment submitted successfully!'));
			}
		} catch (error) {
			console.error('Failed to submit assignment:', error);
			alert($i18n.t('Failed to submit assignment'));
		} finally {
			submitting = false;
		}
	};

	const createAssignment = async () => {
		if (!newAssignment.title || !newAssignment.due_date) {
			alert($i18n.t('Please fill in all required fields'));
			return;
		}

		try {
			creating = true;
			const token = localStorage.getItem('token');
			const result = await createNewAssignment(token, {
				title: newAssignment.title,
				description: newAssignment.description,
				due_date: newAssignment.due_date,
				status: 'pending'
			});

			if (result) {
				// Refresh assignments list
				await loadAssignments();
				
				// Reset form
				newAssignment = {
					title: '',
					description: '',
					due_date: ''
				};
				
				alert($i18n.t('Assignment created successfully!'));
			}
		} catch (error) {
			console.error('Failed to create assignment:', error);
			alert($i18n.t('Failed to create assignment'));
		} finally {
			creating = false;
		}
	};

	const deleteAssignment = async (assignmentId: string) => {
		if (!confirm($i18n.t('Are you sure you want to delete this assignment?'))) {
			return;
		}

		try {
			const token = localStorage.getItem('token');
			await deleteAssignmentById(token, assignmentId);
			await loadAssignments();
			alert($i18n.t('Assignment deleted successfully!'));
		} catch (error) {
			console.error('Failed to delete assignment:', error);
			alert($i18n.t('Failed to delete assignment'));
		}
	};
</script>

<div class="flex flex-col w-full h-full">
	<!-- Header -->
	<div class="px-6 py-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Assignments')}
				</h1>
				<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
					{$i18n.t('Manage and submit your assignments')}
				</p>
			</div>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<!-- Create Assignment Form (Only for Admin) -->
			{#if $user?.role === 'admin'}
				<div class="mb-8 bg-white dark:bg-gray-850 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
						{$i18n.t('Create New Assignment')}
					</h2>
					<div class="space-y-4">
						<div>
							<label
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								for="title"
							>
								{$i18n.t('Title')} *
							</label>
							<input
								id="title"
								type="text"
								bind:value={newAssignment.title}
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder={$i18n.t('Enter assignment title')}
								disabled={creating}
							/>
						</div>
						<div>
							<label
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								for="description"
							>
								{$i18n.t('Description')}
							</label>
							<textarea
								id="description"
								bind:value={newAssignment.description}
								rows="4"
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder={$i18n.t('Enter assignment description')}
								disabled={creating}
							/>
						</div>
						<div>
							<label
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								for="dueDate"
							>
								{$i18n.t('Due Date')} *
							</label>
							<input
								id="dueDate"
								type="date"
								bind:value={newAssignment.due_date}
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								disabled={creating}
							/>
						</div>
						<button
							on:click={createAssignment}
							disabled={creating}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition"
						>
							{creating ? $i18n.t('Creating...') : $i18n.t('Create Assignment')}
						</button>
					</div>
				</div>
			{/if}

			<!-- Loading State -->
			{#if loading}
				<div class="text-center py-12">
					<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
					<p class="mt-2 text-gray-500 dark:text-gray-400">{$i18n.t('Loading assignments...')}</p>
				</div>
			{:else}
				<!-- Assignments List -->
				<div class="space-y-4">
					{#if assignments.length === 0}
						<div class="text-center py-12 text-gray-500 dark:text-gray-400">
							{$i18n.t('No assignments yet')}
						</div>
					{:else}
						{#each assignments as assignment (assignment.id)}
							<div
								class="bg-white dark:bg-gray-850 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 hover:shadow-lg transition"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center gap-3 mb-2">
											<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
												{assignment.title}
											</h3>
											{#if assignment.status === 'submitted'}
												<span
													class="px-3 py-1 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 rounded-full"
												>
													{$i18n.t('Submitted')}
												</span>
											{:else}
												<span
													class="px-3 py-1 text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 rounded-full"
												>
													{$i18n.t('Pending')}
												</span>
											{/if}
										</div>
										<p class="text-gray-600 dark:text-gray-400 mb-3">
											{assignment.description || $i18n.t('No description')}
										</p>
										<div class="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-500">
											<div class="flex items-center gap-1">
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="1.5"
													stroke="currentColor"
													class="size-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"
													/>
												</svg>
												<span>{$i18n.t('Due')}: {assignment.due_date}</span>
											</div>
											{#if assignment.submitted_at}
												<div class="flex items-center gap-1">
													<svg
														xmlns="http://www.w3.org/2000/svg"
														fill="none"
														viewBox="0 0 24 24"
														stroke-width="1.5"
														stroke="currentColor"
														class="size-4"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
														/>
													</svg>
													<span
														>{$i18n.t('Submitted')}: {new Date(
															assignment.submitted_at * 1000
														).toLocaleDateString()}</span
													>
												</div>
											{/if}
										</div>
									</div>
									<div class="flex gap-2">
										{#if assignment.status !== 'submitted'}
											<button
												on:click={() => submitAssignment(assignment.id)}
												disabled={submitting}
												class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white text-sm rounded-lg font-medium transition"
											>
												{submitting ? $i18n.t('Submitting...') : $i18n.t('Submit')}
											</button>
										{/if}
										{#if $user?.role === 'admin'}
											<button
												on:click={() => deleteAssignment(assignment.id)}
												class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg font-medium transition"
											>
												{$i18n.t('Delete')}
											</button>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	/* Custom scrollbar */
	:global(.overflow-y-auto::-webkit-scrollbar) {
		width: 8px;
	}

	:global(.overflow-y-auto::-webkit-scrollbar-track) {
		background: transparent;
	}

	:global(.overflow-y-auto::-webkit-scrollbar-thumb) {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	:global(.dark .overflow-y-auto::-webkit-scrollbar-thumb) {
		background: rgba(75, 85, 99, 0.5);
	}
</style>
