<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	// Get assignment ID from URL
	$: assignmentId = $page.params.id;

	let assignment = null;
	let submissions = [];
	let stats = null;
	let mySubmission = null;
	let loading = true;
	let showDeleteConfirm = false;
	let deleting = false;

	// Check if current user is teacher/admin
	$: isTeacher = ['admin', 'leader', 'teacher'].includes($user?.role);
	$: isStudent = $user?.role === 'student';

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

	// Fetch assignment statistics (for teachers)
	const fetchStats = async () => {
		try {
			const res = await fetch(`/api/metaweb/assignments/${assignmentId}/submissions/stats`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error('Failed to fetch stats');
			}

			stats = await res.json();
		} catch (error) {
			console.error('Error fetching stats:', error);
		}
	};

	// Fetch all submissions (for teachers)
	const fetchSubmissions = async () => {
		try {
			const res = await fetch(
				`/api/metaweb/submissions?assignment_id=${assignmentId}`,
				{
					headers: {
						Authorization: `Bearer ${localStorage.token}`
					}
				}
			);

			if (!res.ok) {
				throw new Error('Failed to fetch submissions');
			}

			submissions = await res.json();
		} catch (error) {
			console.error('Error fetching submissions:', error);
		}
	};

	// Fetch student's own submission
	const fetchMySubmission = async () => {
		try {
			const res = await fetch(
				`/api/metaweb/submissions?assignment_id=${assignmentId}&student_id=${$user.id}`,
				{
					headers: {
						Authorization: `Bearer ${localStorage.token}`
					}
				}
			);

			if (!res.ok) {
				return; // No submission yet
			}

			const data = await res.json();
			mySubmission = data[0] || null;
		} catch (error) {
			console.error('Error fetching my submission:', error);
		}
	};

	// Load all data on mount
	onMount(async () => {
		if (!$user) {
			goto('/');
			return;
		}

		loading = true;
		await fetchAssignment();

		if (isTeacher) {
			await Promise.all([fetchStats(), fetchSubmissions()]);
		} else if (isStudent) {
			await fetchMySubmission();
		}

		loading = false;
	});

	// Format date
	const formatDate = (dateString) => {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleString('zh-CN', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	// Get status badge classes
	const getStatusBadge = (status) => {
		const badges = {
			draft: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
			published: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
			closed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
		};
		return badges[status] || badges.draft;
	};

	// Get submission status badge
	const getSubmissionStatusBadge = (status) => {
		const badges = {
			submitted: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
			ai_reviewing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
			graded: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
			returned: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
		};
		return badges[status] || badges.submitted;
	};

	// Navigate to submit page
	const goToSubmit = () => {
		goto(`/workspace/assignments/${assignmentId}/submit`);
	};

	// Navigate to grade page
	const goToGrade = (submissionId) => {
		goto(`/workspace/assignments/${assignmentId}/grade/${submissionId}`);
	};

	// Publish assignment (with confirmation)
	let showPublishConfirm = false;
	let publishing = false;

	const publishAssignment = async () => {
		publishing = true;
		try {
			const res = await fetch(`/api/metaweb/assignments/${assignmentId}/publish`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error('Failed to publish assignment');
			}

			toast.success($i18n.t('Assignment published'));
			showPublishConfirm = false;
			await fetchAssignment();
		} catch (error) {
			console.error('Error publishing assignment:', error);
			toast.error($i18n.t('Failed to publish assignment'));
		} finally {
			publishing = false;
		}
	};

	// Delete assignment (only for drafts)
	const deleteAssignment = async () => {
		deleting = true;
		try {
			const res = await fetch(`/api/metaweb/assignments/${assignmentId}`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error('Failed to delete assignment');
			}

			toast.success($i18n.t('Assignment deleted'));
			goto('/workspace/assignments');
		} catch (error) {
			console.error('Error deleting assignment:', error);
			toast.error($i18n.t('Failed to delete assignment'));
			deleting = false;
		}
	};

	// Check if assignment is overdue
	const isOverdue = () => {
		if (!assignment?.due_date) return false;
		return new Date(assignment.due_date) < new Date();
	};

	// Check if student can submit
	const canSubmit = () => {
		if (!assignment) return false;
		if (assignment.status !== 'published') return false;
		if (mySubmission) return false; // Already submitted
		if (!assignment.allow_late_submission && isOverdue()) return false;
		return true;
	};
</script>

{#if loading}
	<div class="flex items-center justify-center h-96">
		<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white" />
	</div>
{:else if assignment}
	<div class="max-w-6xl mx-auto p-6">
		<!-- Header -->
		<div class="mb-6">
			<div class="flex items-center justify-between mb-4">
				<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
					{assignment.title}
				</h1>
				<span class="px-3 py-1 rounded-full text-sm font-medium {getStatusBadge(assignment.status)}">
					{$i18n.t(assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1))}
				</span>
			</div>

			<div class="flex gap-4 text-sm text-gray-600 dark:text-gray-400">
				<span>{$i18n.t('Subject')}: {assignment.subject}</span>
				<span>|</span>
				<span>{$i18n.t('Grade')}: {assignment.grade_level}</span>
				<span>|</span>
				<span>{$i18n.t('Total Points')}: {assignment.total_points}</span>
				{#if assignment.due_date}
					<span>|</span>
					<span class:text-red-600={isOverdue()}>
						{$i18n.t('Due')}: {formatDate(assignment.due_date)}
					</span>
				{/if}
			</div>
		</div>

		<!-- Teacher View -->
		{#if isTeacher}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
				<!-- Assignment Info Card -->
				<div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
						{$i18n.t('Assignment Details')}
					</h2>

					{#if assignment.description}
						<div class="prose dark:prose-invert max-w-none mb-4">
							{@html assignment.description}
						</div>
					{/if}

					{#if assignment.grading_rubric}
						<div class="mt-4">
							<h3 class="font-semibold text-gray-900 dark:text-white mb-2">
								{$i18n.t('Grading Rubric')}
							</h3>
							<div class="prose dark:prose-invert max-w-none">
								{@html assignment.grading_rubric}
							</div>
						</div>
					{/if}

					{#if assignment.files && assignment.files.length > 0}
						<div class="mt-4">
							<h3 class="font-semibold text-gray-900 dark:text-white mb-2">
								{$i18n.t('Attachments')}
							</h3>
							<div class="space-y-2">
								{#each assignment.files as file}
									<a
										href={file.url}
										target="_blank"
										class="flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:underline"
									>
										<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
											<path d="M8 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0017.414 6L14 2.586A2 2 0 0012.586 2H8z" />
										</svg>
										{file.name}
									</a>
								{/each}
							</div>
						</div>
					{/if}

					{#if assignment.status === 'draft'}
						<div class="mt-6 flex gap-3">
							<button
								on:click={() => showPublishConfirm = true}
								class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
							>
								{$i18n.t('Publish Assignment')}
							</button>
							<button
								on:click={() => goto(`/workspace/assignments/${assignmentId}/edit`)}
								class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
							>
								{$i18n.t('Edit')}
							</button>
							<button
								on:click={() => showDeleteConfirm = true}
								class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
							>
								{$i18n.t('Delete')}
							</button>
						</div>
					{/if}
				</div>

				<!-- Statistics Card -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
						{$i18n.t('Statistics')}
					</h2>

					{#if stats}
						<div class="space-y-4">
							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Submitted')}</div>
								<div class="text-2xl font-bold text-gray-900 dark:text-white">
									{stats.submitted_count || 0}
								</div>
							</div>
							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Graded')}</div>
								<div class="text-2xl font-bold text-gray-900 dark:text-white">
									{stats.graded_count || 0}
								</div>
							</div>
							{#if stats.average_score !== null}
								<div>
									<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Average Score')}</div>
									<div class="text-2xl font-bold text-gray-900 dark:text-white">
										{stats.average_score.toFixed(1)} / {assignment.total_points}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			<!-- Submissions List -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow">
				<div class="p-6 border-b border-gray-200 dark:border-gray-700">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Submissions')} ({submissions.length})
					</h2>
				</div>

				<div class="overflow-x-auto">
					<table class="w-full">
						<thead class="bg-gray-50 dark:bg-gray-700">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
									{$i18n.t('Student')}
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
									{$i18n.t('Submitted At')}
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
									{$i18n.t('Status')}
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
									{$i18n.t('Score')}
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
									{$i18n.t('Actions')}
								</th>
							</tr>
						</thead>
						<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
							{#if submissions.length === 0}
								<tr>
									<td colspan="5" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
										{$i18n.t('No submissions yet')}
									</td>
								</tr>
							{:else}
								{#each submissions as submission}
									<tr class="hover:bg-gray-50 dark:hover:bg-gray-700 transition">
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
											{submission.student_name || submission.student_id}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
											{formatDate(submission.submitted_at)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span class="px-2 py-1 text-xs font-medium rounded-full {getSubmissionStatusBadge(submission.status)}">
												{$i18n.t(submission.status)}
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
											{#if submission.teacher_score !== null}
												{submission.teacher_score} / {assignment.total_points}
											{:else if submission.ai_score !== null}
												AI: {submission.ai_score} / {assignment.total_points}
											{:else}
												-
											{/if}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm">
											<button
												on:click={() => goToGrade(submission.id)}
												class="text-blue-600 dark:text-blue-400 hover:underline"
											>
												{submission.status === 'graded' || submission.status === 'returned'
													? $i18n.t('View')
													: $i18n.t('Grade')}
											</button>
										</td>
									</tr>
								{/each}
							{/if}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

		<!-- Student View -->
		{#if isStudent}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Assignment Details -->
				<div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
						{$i18n.t('Assignment Requirements')}
					</h2>

					{#if assignment.description}
						<div class="prose dark:prose-invert max-w-none mb-4">
							{@html assignment.description}
						</div>
					{/if}

					{#if assignment.files && assignment.files.length > 0}
						<div class="mt-4">
							<h3 class="font-semibold text-gray-900 dark:text-white mb-2">
								{$i18n.t('Attachments')}
							</h3>
							<div class="space-y-2">
								{#each assignment.files as file}
									<a
										href={file.url}
										target="_blank"
										class="flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:underline"
									>
										<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
											<path d="M8 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0017.414 6L14 2.586A2 2 0 0012.586 2H8z" />
										</svg>
										{file.name}
									</a>
								{/each}
							</div>
						</div>
					{/if}

					{#if canSubmit()}
						<button
							on:click={goToSubmit}
							class="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition font-medium"
						>
							{$i18n.t('Submit Assignment')}
						</button>
					{:else if mySubmission}
						<div class="mt-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
							<p class="text-green-800 dark:text-green-300">
								{$i18n.t('You have submitted this assignment')}
							</p>
						</div>
					{:else if isOverdue()}
						<div class="mt-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
							<p class="text-red-800 dark:text-red-300">
								{$i18n.t('This assignment is overdue')}
							</p>
						</div>
					{/if}
				</div>

				<!-- My Submission Status -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
						{$i18n.t('My Submission')}
					</h2>

					{#if mySubmission}
						<div class="space-y-4">
							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Status')}</div>
								<span class="inline-block mt-1 px-2 py-1 text-xs font-medium rounded-full {getSubmissionStatusBadge(mySubmission.status)}">
									{$i18n.t(mySubmission.status)}
								</span>
							</div>
							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Submitted At')}</div>
								<div class="text-sm text-gray-900 dark:text-white">
									{formatDate(mySubmission.submitted_at)}
								</div>
							</div>
							{#if mySubmission.teacher_score !== null}
								<div>
									<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Score')}</div>
									<div class="text-2xl font-bold text-gray-900 dark:text-white">
										{mySubmission.teacher_score} / {assignment.total_points}
									</div>
								</div>
							{:else if mySubmission.ai_score !== null}
								<div>
									<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('AI Score (Preliminary)')}</div>
									<div class="text-xl font-bold text-gray-900 dark:text-white">
										{mySubmission.ai_score} / {assignment.total_points}
									</div>
								</div>
							{/if}
							{#if mySubmission.teacher_feedback || mySubmission.ai_feedback}
								<div>
									<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">{$i18n.t('Feedback')}</div>
									<div class="prose dark:prose-invert max-w-none text-sm">
										{@html mySubmission.teacher_feedback || mySubmission.ai_feedback}
									</div>
								</div>
							{/if}
							<button
								on:click={() => goToGrade(mySubmission.id)}
								class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
							>
								{$i18n.t('View Details')}
							</button>
						</div>
					{:else}
						<p class="text-gray-600 dark:text-gray-400 text-sm">
							{$i18n.t('You have not submitted this assignment yet')}
						</p>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center h-96">
		<p class="text-gray-600 dark:text-gray-400">
			{$i18n.t('Assignment not found')}
		</p>
	</div>
{/if}

<!-- Publish Confirmation Modal -->
{#if showPublishConfirm}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showPublishConfirm = false}>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4" on:click|stopPropagation>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
				{$i18n.t('Confirm Publish')}
			</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">
				{$i18n.t('Are you sure you want to publish this assignment? Students will be able to see and submit their work.')}
			</p>
			<div class="flex justify-end gap-3">
				<button
					on:click={() => showPublishConfirm = false}
					disabled={publishing}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					on:click={publishAssignment}
					disabled={publishing}
					class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition disabled:opacity-50"
				>
					{publishing ? $i18n.t('Publishing...') : $i18n.t('Publish')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteConfirm}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showDeleteConfirm = false}>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4" on:click|stopPropagation>
			<h3 class="text-lg font-semibold text-red-600 dark:text-red-400 mb-4">
				{$i18n.t('Confirm Delete')}
			</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">
				{$i18n.t('Are you sure you want to delete this assignment? This action cannot be undone.')}
			</p>
			<div class="flex justify-end gap-3">
				<button
					on:click={() => showDeleteConfirm = false}
					disabled={deleting}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					on:click={deleteAssignment}
					disabled={deleting}
					class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition disabled:opacity-50"
				>
					{deleting ? $i18n.t('Deleting...') : $i18n.t('Delete')}
				</button>
			</div>
		</div>
	</div>
{/if}
