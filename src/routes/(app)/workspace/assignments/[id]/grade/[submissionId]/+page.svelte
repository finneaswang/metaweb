<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	// Route params
	$: assignmentId = $page.params.id;
	$: submissionId = $page.params.submissionId;

	let assignment = null;
	let submission = null;
	let loading = true;
	let saving = false;
	let showSubmitConfirm = false;
	let showReturnConfirm = false;

	// Grading form
	let teacherScore = 0;
	let teacherFeedback = '';
	let teacherComments = '';
	let useAiScore = false;

	// Fetch assignment and submission data
	const fetchData = async () => {
		loading = true;
		try {
			const [assignmentRes, submissionRes] = await Promise.all([
				fetch(`/api/metaweb/assignments/${assignmentId}`, {
					headers: { Authorization: `Bearer ${localStorage.token}` }
				}),
				fetch(`/api/metaweb/submissions/${submissionId}`, {
					headers: { Authorization: `Bearer ${localStorage.token}` }
				})
			]);

			if (!assignmentRes.ok || !submissionRes.ok) {
				throw new Error('Failed to fetch data');
			}

			assignment = await assignmentRes.json();
			submission = await submissionRes.json();

			// Initialize form with existing data
			if (submission.teacher_score !== null) {
				teacherScore = submission.teacher_score;
			}
			if (submission.teacher_feedback) {
				teacherFeedback = submission.teacher_feedback;
			}
			if (submission.teacher_detailed_comments) {
				teacherComments = submission.teacher_detailed_comments;
			}
		} catch (error) {
			console.error('Error fetching data:', error);
			toast.error($i18n.t('Failed to load grading data'));
			goto(`/workspace/assignments/${assignmentId}`);
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (!$user) {
			goto('/');
			return;
		}

		// Check permission
		const isTeacher = ['admin', 'leader', 'teacher'].includes($user?.role);
		if (!isTeacher) {
			toast.error($i18n.t('Access denied'));
			goto('/');
			return;
		}

		await fetchData();
	});

	// Use AI score
	const applyAiScore = () => {
		if (submission?.ai_score !== null) {
			teacherScore = submission.ai_score;
			useAiScore = true;
			toast.success($i18n.t('AI score applied'));
		}
	};

	// Save draft
	const saveDraft = async () => {
		saving = true;
		try {
			const res = await fetch(`/api/metaweb/submissions/${submissionId}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					teacher_score: teacherScore || null,
					teacher_feedback: teacherFeedback || null,
					teacher_detailed_comments: teacherComments || null
				})
			});

			if (!res.ok) throw new Error('Failed to save draft');

			toast.success($i18n.t('Draft saved'));
		} catch (error) {
			console.error('Error saving draft:', error);
			toast.error($i18n.t('Failed to save draft'));
		} finally {
			saving = false;
		}
	};

	// Submit grading
	const submitGrading = async () => {
		if (teacherScore === null || teacherScore === 0) {
			toast.error($i18n.t('Please enter a score'));
			return;
		}

		if (teacherScore > assignment.total_points) {
			toast.error($i18n.t('Score cannot exceed total points'));
			return;
		}

		saving = true;
		try {
			const res = await fetch(`/api/metaweb/submissions/${submissionId}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					teacher_score: teacherScore,
					teacher_feedback: teacherFeedback || null,
					teacher_detailed_comments: teacherComments || null,
					status: 'graded'
				})
			});

			if (!res.ok) throw new Error('Failed to submit grading');

			toast.success($i18n.t('Grading submitted successfully'));
			goto(`/workspace/assignments/${assignmentId}`);
		} catch (error) {
			console.error('Error submitting grading:', error);
			toast.error($i18n.t('Failed to submit grading'));
		} finally {
			saving = false;
		}
	};

	// Return to student
	const returnToStudent = async () => {
		if (teacherScore === null || teacherScore === 0) {
			toast.error($i18n.t('Please enter a score'));
			return;
		}

		saving = true;
		try {
			const res = await fetch(`/api/metaweb/submissions/${submissionId}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					teacher_score: teacherScore,
					teacher_feedback: teacherFeedback || null,
					teacher_detailed_comments: teacherComments || null,
					status: 'returned'
				})
			});

			if (!res.ok) throw new Error('Failed to return submission');

			toast.success($i18n.t('Submission returned to student'));
			goto(`/workspace/assignments/${assignmentId}`);
		} catch (error) {
			console.error('Error returning submission:', error);
			toast.error($i18n.t('Failed to return submission'));
		} finally {
			saving = false;
		}
	};

	// Format date
	const formatDate = (dateString) => {
		if (!dateString) return '';
		return new Date(dateString).toLocaleString('zh-CN');
	};

	// Get file extension
	const getFileExtension = (filename) => {
		return filename.split('.').pop().toLowerCase();
	};

	// Check if file is image
	const isImage = (filename) => {
		const ext = getFileExtension(filename);
		return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext);
	};

	// Check if file is PDF
	const isPdf = (filename) => {
		return getFileExtension(filename) === 'pdf';
	};
</script>

<svelte:head>
	<title>{$i18n.t('Grade Submission')} | {$i18n.t('Open WebUI')}</title>
</svelte:head>

<div class="flex flex-col h-full">
	{#if loading}
		<div class="flex justify-center items-center h-full">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else if assignment && submission}
		<!-- Header -->
		<div class="p-4 border-b border-gray-200 dark:border-gray-700">
			<button
				class="text-blue-600 dark:text-blue-400 hover:underline mb-2 flex items-center gap-1"
				on:click={() => goto(`/workspace/assignments/${assignmentId}`)}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-4 h-4"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
				</svg>
				{$i18n.t('Back to Assignment')}
			</button>
			<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
				{$i18n.t('Grade Submission')}
			</h1>
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
				{assignment.title} - {submission.student?.name || 'Unknown Student'}
			</p>
		</div>

		<!-- Main Content -->
		<div class="flex-1 overflow-hidden flex flex-col lg:flex-row">
			<!-- Left Panel - Student Answer -->
			<div class="flex-1 overflow-y-auto p-4 border-r border-gray-200 dark:border-gray-700">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
					{$i18n.t('Student Answer')}
				</h2>

				<!-- Submission Info -->
				<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 mb-4">
					<div class="grid grid-cols-2 gap-2 text-sm">
						<div>
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Submitted at')}:</span>
							<span class="ml-2 text-gray-900 dark:text-white"
								>{formatDate(submission.created_at)}</span
							>
						</div>
						<div>
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Answer Type')}:</span>
							<span class="ml-2 text-gray-900 dark:text-white">{submission.answer_type}</span>
						</div>
					</div>
				</div>

				<!-- Answer Content -->
				{#if submission.answer_type === 'file'}
					<div class="space-y-4">
						{#if submission.answer_files && submission.answer_files.length > 0}
							{#each submission.answer_files as file}
								<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
									<div class="flex items-center justify-between mb-2">
										<span class="font-medium text-gray-900 dark:text-white">{file.name}</span>
										<a
											href={file.url}
											target="_blank"
											class="text-blue-600 dark:text-blue-400 hover:underline text-sm"
										>
											{$i18n.t('Download')}
										</a>
									</div>

									<!-- Image Preview -->
									{#if isImage(file.name)}
										<img
											src={file.url}
											alt={file.name}
											class="max-w-full h-auto rounded border border-gray-300 dark:border-gray-600"
										/>
									{:else if isPdf(file.name)}
										<iframe
											src={file.url}
											title={file.name}
											class="w-full h-96 border border-gray-300 dark:border-gray-600 rounded"
										></iframe>
									{:else}
										<div
											class="flex items-center justify-center h-32 bg-gray-100 dark:bg-gray-700 rounded"
										>
											<p class="text-gray-600 dark:text-gray-400">
												{$i18n.t('Preview not available')}
											</p>
										</div>
									{/if}
								</div>
							{/each}
						{:else}
							<p class="text-gray-600 dark:text-gray-400">{$i18n.t('No files submitted')}</p>
						{/if}
					</div>
				{:else if submission.answer_type === 'text'}
					<div class="prose dark:prose-invert max-w-none">
						<div class="whitespace-pre-wrap">{submission.answer_text || 'No answer'}</div>
					</div>
				{:else if submission.answer_type === 'url'}
					<div class="space-y-2">
						<p class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Submitted URL')}:</p>
						<a
							href={submission.answer_text}
							target="_blank"
							class="text-blue-600 dark:text-blue-400 hover:underline break-all"
						>
							{submission.answer_text}
						</a>
					</div>
				{/if}
			</div>

			<!-- Right Panel - Grading Form -->
			<div class="w-full lg:w-96 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
					{$i18n.t('Grading')}
				</h2>

				<!-- AI Analysis (if available) -->
				{#if submission.ai_score !== null || submission.ai_feedback}
					<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-4 border border-blue-200 dark:border-blue-800">
						<h3 class="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-3 flex items-center gap-2">
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
									d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
								/>
							</svg>
							{$i18n.t('AI Analysis')}
						</h3>

						{#if submission.ai_score !== null}
							<div class="mb-3">
								<p class="text-xs text-blue-800 dark:text-blue-400 mb-1">
									{$i18n.t('AI Score')}:
								</p>
								<p class="text-2xl font-bold text-blue-900 dark:text-blue-300">
									{submission.ai_score}/{assignment.total_points}
								</p>
								<button
									class="mt-2 text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
									on:click={applyAiScore}
									disabled={useAiScore}
								>
									{useAiScore ? $i18n.t('AI Score Applied') : $i18n.t('Use AI Score')}
								</button>
							</div>
						{/if}

						{#if submission.ai_feedback}
							<div>
								<p class="text-xs text-blue-800 dark:text-blue-400 mb-1">
									{$i18n.t('AI Feedback')}:
								</p>
								<p class="text-sm text-blue-900 dark:text-blue-200 whitespace-pre-wrap">
									{submission.ai_feedback}
								</p>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Grading Form -->
				<form on:submit|preventDefault={() => showSubmitConfirm = true} class="space-y-4">
					<!-- Score Input -->
					<div>
						<label
							for="score"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							{$i18n.t('Score')} <span class="text-red-500">*</span>
						</label>
						<div class="flex items-center gap-2">
							<input
								type="number"
								id="score"
								bind:value={teacherScore}
								min="0"
								max={assignment.total_points}
								step="0.5"
								class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
								required
							/>
							<span class="text-gray-600 dark:text-gray-400">/ {assignment.total_points}</span>
						</div>
					</div>

					<!-- Feedback Input -->
					<div>
						<label
							for="feedback"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							{$i18n.t('Feedback')}
						</label>
						<textarea
							id="feedback"
							bind:value={teacherFeedback}
							rows="4"
							placeholder={$i18n.t('Enter your feedback here...')}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 resize-none"
						></textarea>
					</div>

					<!-- Detailed Comments -->
					<div>
						<label
							for="comments"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							{$i18n.t('Detailed Comments')} ({$i18n.t('Optional')})
						</label>
						<textarea
							id="comments"
							bind:value={teacherComments}
							rows="6"
							placeholder={$i18n.t('Enter detailed comments...')}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 resize-none"
						></textarea>
					</div>

					<!-- Action Buttons -->
					<div class="space-y-2 pt-4">
						<button
							type="button"
							on:click={saveDraft}
							disabled={saving}
							class="w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition disabled:opacity-50"
						>
							{saving ? $i18n.t('Saving...') : $i18n.t('Save Draft')}
						</button>

						<button
							type="submit"
							disabled={saving}
							class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
						>
							{saving ? $i18n.t('Submitting...') : $i18n.t('Submit Grading')}
						</button>

						<button
							type="button"
							on:click={() => showReturnConfirm = true}
							disabled={saving}
							class="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
						>
							{saving ? $i18n.t('Returning...') : $i18n.t('Return to Student')}
						</button>
					</div>
				</form>
			</div>
		</div>
	{/if}
</div>

<!-- Submit Grading Confirmation Modal -->
{#if showSubmitConfirm}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showSubmitConfirm = false}>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4" on:click|stopPropagation>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
				{$i18n.t("Confirm Submit Grading")}
			</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">
				{$i18n.t("Are you sure you want to submit the grading? The student will be able to see the score and feedback.")}
			</p>
			<div class="flex justify-end gap-3">
				<button
					on:click={() => showSubmitConfirm = false}
					disabled={saving}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
				>
					{$i18n.t("Cancel")}
				</button>
				<button
					on:click={submitGrading}
					disabled={saving}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
				>
					{saving ? $i18n.t("Submitting...") : $i18n.t("Submit")}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Return to Student Confirmation Modal -->
{#if showReturnConfirm}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showReturnConfirm = false}>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4" on:click|stopPropagation>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
				{$i18n.t("Confirm Return to Student")}
			</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">
				{$i18n.t("Are you sure you want to return this submission to the student? They will be able to see your feedback.")}
			</p>
			<div class="flex justify-end gap-3">
				<button
					on:click={() => showReturnConfirm = false}
					disabled={saving}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
				>
					{$i18n.t("Cancel")}
				</button>
				<button
					on:click={returnToStudent}
					disabled={saving}
					class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition disabled:opacity-50"
				>
					{saving ? $i18n.t("Returning...") : $i18n.t("Return")}
				</button>
			</div>
		</div>
	</div>
{/if}
