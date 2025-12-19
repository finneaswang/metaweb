<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	$: assignmentId = $page.params.id;

	let assignment = null;
	let loading = true;
	let submitting = false;

	// Submission type: 'file' | 'text' | 'url'
	let submissionType = 'file';

	// File upload
	let files = [];
	let uploadProgress = 0;

	// Text input
	let textAnswer = '';

	// URL input
	let urlAnswer = '';

	// Fetch assignment details
	const fetchAssignment = async () => {
		try {
			const res = await fetch(`/api/metaweb/assignments/${assignmentId}`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error('Failed to fetch assignment');
			}

			assignment = await res.json();
		} catch (error) {
			console.error('Error fetching assignment:', error);
			toast.error($i18n.t('Failed to load assignment'));
			goto('/workspace/assignments');
		}
	};

	onMount(async () => {
		if (!$user || $user.role !== 'student') {
			toast.error($i18n.t('Access denied'));
			goto('/workspace/assignments');
			return;
		}

		loading = true;
		await fetchAssignment();
		loading = false;
	});

	// Handle file selection
	const handleFileSelect = (event) => {
		const selectedFiles = Array.from(event.target.files);
		files = [...files, ...selectedFiles];
	};

	// Remove file from list
	const removeFile = (index) => {
		files = files.filter((_, i) => i !== index);
	};

	// Upload files to server
	const uploadFiles = async (submissionId) => {
		if (files.length === 0) return [];

		const formData = new FormData();
		files.forEach(file => formData.append('files', file));

		try {
			const res = await fetch(`/api/metaweb/submissions/${submissionId}/files`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				},
				body: formData
			});

			if (!res.ok) {
				throw new Error('Failed to upload files');
			}

			const data = await res.json();
			return data.files || [];
		} catch (error) {
			console.error('Error uploading files:', error);
			throw error;
		}
	};

	// Submit assignment
	const submitAssignment = async () => {
		// Validation
		if (submissionType === 'file' && files.length === 0) {
			toast.error($i18n.t('Please select at least one file'));
			return;
		}
		if (submissionType === 'text' && !textAnswer.trim()) {
			toast.error($i18n.t('Please enter your answer'));
			return;
		}
		if (submissionType === 'url' && !urlAnswer.trim()) {
			toast.error($i18n.t('Please enter a URL'));
			return;
		}

		// Confirm submission
		const confirmed = confirm($i18n.t('Are you sure you want to submit? You cannot modify after submission.'));
		if (!confirmed) return;

		submitting = true;
		uploadProgress = 0;

		try {
			// Step 1: Create submission
			const submissionData = {
				assignment_id: assignmentId,
				answer_type: submissionType,
				answer_text: submissionType === 'text' ? textAnswer : (submissionType === 'url' ? urlAnswer : ''),
				answer_files: []
			};

			const createRes = await fetch('/api/metaweb/submissions', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(submissionData)
			});

			if (!createRes.ok) {
				throw new Error('Failed to create submission');
			}

			const submission = await createRes.json();
			uploadProgress = 30;

			// Step 2: Upload files if any
			if (submissionType === 'file' && files.length > 0) {
				const uploadedFiles = await uploadFiles(submission.id);
				uploadProgress = 70;

				// Step 3: Update submission with file info
				await fetch(`/api/metaweb/submissions/${submission.id}`, {
					method: 'PATCH',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.token}`
					},
					body: JSON.stringify({
						answer_files: uploadedFiles
					})
				});
			}

			uploadProgress = 100;
			toast.success($i18n.t('Assignment submitted successfully'));

			// Redirect to assignment detail page
			setTimeout(() => {
				goto(`/workspace/assignments/${assignmentId}`);
			}, 1000);
		} catch (error) {
			console.error('Error submitting assignment:', error);
			toast.error($i18n.t('Failed to submit assignment'));
		} finally {
			submitting = false;
		}
	};

	// Format file size
	const formatFileSize = (bytes) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
	};
</script>

{#if loading}
	<div class="flex items-center justify-center h-96">
		<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white" />
	</div>
{:else if assignment}
	<div class="max-w-4xl mx-auto p-6">
		<!-- Header -->
		<div class="mb-6">
			<button
				on:click={() => goto(`/workspace/assignments/${assignmentId}`)}
				class="text-blue-600 dark:text-blue-400 hover:underline mb-4 flex items-center gap-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				{$i18n.t('Back to Assignment')}
			</button>

			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
				{$i18n.t('Submit Assignment')}
			</h1>
			<h2 class="text-xl text-gray-600 dark:text-gray-400">
				{assignment.title}
			</h2>
		</div>

		<!-- Assignment Info -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
			<h3 class="font-semibold text-gray-900 dark:text-white mb-3">
				{$i18n.t('Assignment Requirements')}
			</h3>
			{#if assignment.description}
				<div class="prose dark:prose-invert max-w-none text-sm">
					{@html assignment.description}
				</div>
			{/if}
			<div class="mt-4 flex gap-4 text-sm text-gray-600 dark:text-gray-400">
				<span>{$i18n.t('Total Points')}: {assignment.total_points}</span>
				{#if assignment.due_date}
					<span>|</span>
					<span>{$i18n.t('Due')}: {new Date(assignment.due_date).toLocaleString('zh-CN')}</span>
				{/if}
			</div>
		</div>

		<!-- Submission Type Selection -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
			<h3 class="font-semibold text-gray-900 dark:text-white mb-4">
				{$i18n.t('Select Submission Type')}
			</h3>
			<div class="flex gap-4">
				<button
					on:click={() => submissionType = 'file'}
					class="flex-1 p-4 border-2 rounded-lg transition {submissionType === 'file'
						? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
						: 'border-gray-300 dark:border-gray-600 hover:border-blue-400'}"
				>
					<svg class="w-8 h-8 mx-auto mb-2 {submissionType === 'file' ? 'text-blue-600' : 'text-gray-400'}" fill="currentColor" viewBox="0 0 20 20">
						<path d="M8 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0017.414 6L14 2.586A2 2 0 0012.586 2H8z" />
					</svg>
					<div class="font-medium text-gray-900 dark:text-white">{$i18n.t('File Upload')}</div>
					<div class="text-xs text-gray-500 mt-1">{$i18n.t('PDF, Images, Documents')}</div>
				</button>

				<button
					on:click={() => submissionType = 'text'}
					class="flex-1 p-4 border-2 rounded-lg transition {submissionType === 'text'
						? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
						: 'border-gray-300 dark:border-gray-600 hover:border-blue-400'}"
				>
					<svg class="w-8 h-8 mx-auto mb-2 {submissionType === 'text' ? 'text-blue-600' : 'text-gray-400'}" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clip-rule="evenodd" />
					</svg>
					<div class="font-medium text-gray-900 dark:text-white">{$i18n.t('Text Answer')}</div>
					<div class="text-xs text-gray-500 mt-1">{$i18n.t('Write your answer')}</div>
				</button>

				<button
					on:click={() => submissionType = 'url'}
					class="flex-1 p-4 border-2 rounded-lg transition {submissionType === 'url'
						? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
						: 'border-gray-300 dark:border-gray-600 hover:border-blue-400'}"
				>
					<svg class="w-8 h-8 mx-auto mb-2 {submissionType === 'url' ? 'text-blue-600' : 'text-gray-400'}" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clip-rule="evenodd" />
					</svg>
					<div class="font-medium text-gray-900 dark:text-white">{$i18n.t('URL Link')}</div>
					<div class="text-xs text-gray-500 mt-1">{$i18n.t('Online document link')}</div>
				</button>
			</div>
		</div>

		<!-- Submission Form -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
			{#if submissionType === 'file'}
				<!-- File Upload -->
				<div>
					<label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
						{$i18n.t('Upload Files')}
					</label>
					<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
						<svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
						</svg>
						<label class="cursor-pointer">
							<span class="text-blue-600 dark:text-blue-400 hover:underline">
								{$i18n.t('Click to upload')}
							</span>
							<span class="text-gray-500"> {$i18n.t('or drag and drop')}</span>
							<input
								type="file"
								multiple
								accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.gif"
								on:change={handleFileSelect}
								class="hidden"
							/>
						</label>
						<p class="text-xs text-gray-500 mt-2">
							{$i18n.t('PDF, DOC, DOCX, JPG, PNG (max 20MB each)')}
						</p>
					</div>

					{#if files.length > 0}
						<div class="mt-4 space-y-2">
							{#each files as file, index}
								<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
									<div class="flex items-center gap-3 flex-1">
										<svg class="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
											<path d="M8 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0017.414 6L14 2.586A2 2 0 0012.586 2H8z" />
										</svg>
										<div class="flex-1 min-w-0">
											<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
												{file.name}
											</div>
											<div class="text-xs text-gray-500">
												{formatFileSize(file.size)}
											</div>
										</div>
									</div>
									<button
										on:click={() => removeFile(index)}
										class="text-red-600 hover:text-red-700 p-1"
									>
										<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>

			{:else if submissionType === 'text'}
				<!-- Text Input -->
				<div>
					<label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
						{$i18n.t('Your Answer')}
					</label>
					<textarea
						bind:value={textAnswer}
						rows="12"
						class="w-full rounded-lg border border-gray-300 dark:border-gray-600 p-3 text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						placeholder={$i18n.t('Enter your answer here...')}
					/>
					<p class="text-xs text-gray-500 mt-2">
						{$i18n.t('You can use Markdown formatting')}
					</p>
				</div>

			{:else if submissionType === 'url'}
				<!-- URL Input -->
				<div>
					<label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
						{$i18n.t('Document URL')}
					</label>
					<input
						type="url"
						bind:value={urlAnswer}
						class="w-full rounded-lg border border-gray-300 dark:border-gray-600 p-3 text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						placeholder="https://..."
					/>
					<p class="text-xs text-gray-500 mt-2">
						{$i18n.t('Enter the link to your online document (e.g., Google Docs, Notion)')}
					</p>
				</div>
			{/if}

			<!-- Upload Progress -->
			{#if submitting && uploadProgress > 0}
				<div class="mt-6">
					<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
						<span>{$i18n.t('Uploading...')}</span>
						<span>{uploadProgress}%</span>
					</div>
					<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
						<div
							class="bg-blue-600 h-2 rounded-full transition-all duration-300"
							style="width: {uploadProgress}%"
						/>
					</div>
				</div>
			{/if}

			<!-- Submit Button -->
			<div class="mt-6 flex gap-3">
				<button
					on:click={submitAssignment}
					disabled={submitting}
					class="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition font-medium"
				>
					{submitting ? $i18n.t('Submitting...') : $i18n.t('Submit Assignment')}
				</button>
				<button
					on:click={() => goto(`/workspace/assignments/${assignmentId}`)}
					disabled={submitting}
					class="px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition"
				>
					{$i18n.t('Cancel')}
				</button>
			</div>
		</div>
	</div>
{/if}
