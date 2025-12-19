<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let loading = false;
	let uploading = false;

	// Form fields
	let title = '';
	let description = '';
	let subject = '';
	let gradeLevel = '';
	let dueDate = '';
	let totalPoints = 100;
	let gradingMode = 'manual';
	let gradingRubric = '';
	let allowLateSubmission = true;
	let latePenaltyPercent = 10;
	let files = [];

	// Subject options
	const subjects = [
		{ value: '数学', label: '数学' },
		{ value: '物理', label: '物理' },
		{ value: '化学', label: '化学' },
		{ value: '英语', label: '英语' },
		{ value: '语文', label: '语文' },
		{ value: '生物', label: '生物' },
		{ value: '历史', label: '历史' },
		{ value: '地理', label: '地理' }
	];

	// Grade level options
	const gradeLevels = [
		{ value: '初中', label: '初中' },
		{ value: '高中', label: '高中' }
	];

	// Grading mode options
	const gradingModes = [
		{ value: 'manual', label: '纯人工批改', description: '教师手动批改所有作业' },
		{ value: 'ai_draft', label: 'AI草稿，教师审核', description: 'AI先批改，教师审核确认' },
		{ value: 'ai_auto', label: 'AI自动批改', description: 'AI自动批改并返回给学生' }
	];

	onMount(() => {
		if (!$user) {
			goto('/');
			return;
		}

		const isTeacher = ['admin', 'leader', 'teacher'].includes($user?.role);
		if (!isTeacher) {
			toast.error($i18n.t('Access denied'));
			goto('/');
			return;
		}
	});

	// File selection
	const handleFileSelect = (event) => {
		const selectedFiles = Array.from(event.target.files);
		files = [...files, ...selectedFiles];
	};

	// Remove file
	const removeFile = (index) => {
		files = files.filter((_, i) => i !== index);
	};

	// Format file size
	const formatFileSize = (bytes) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
	};

	// Create assignment
	const createAssignment = async (isDraft = false) => {
		if (!title.trim()) {
			toast.error($i18n.t('Please enter assignment title'));
			return;
		}

		if (!subject) {
			toast.error($i18n.t('Please select a subject'));
			return;
		}

		if (!gradeLevel) {
			toast.error($i18n.t('Please select grade level'));
			return;
		}

		if (!dueDate) {
			toast.error($i18n.t('Please select due date'));
			return;
		}

		loading = true;

		try {
			// Step 1: Create assignment
			const assignmentData = {
				title: title.trim(),
				description: description.trim() || null,
				subject,
				grade_level: gradeLevel,
				due_date: new Date(dueDate).toISOString(),
				total_points: totalPoints,
				grading_mode: gradingMode,
				grading_rubric: gradingRubric.trim() || null,
				allow_late_submission: allowLateSubmission,
				late_penalty_percent: allowLateSubmission ? latePenaltyPercent : 0,
				status: isDraft ? 'draft' : 'published'
			};

			const res = await fetch('/api/metaweb/assignments', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(assignmentData)
			});

			if (!res.ok) {
				const error = await res.text();
				throw new Error(error || 'Failed to create assignment');
			}

			const assignment = await res.json();

			// Step 2: Upload files if any
			if (files.length > 0) {
				uploading = true;
				const formData = new FormData();
				files.forEach((file) => formData.append('files', file));

				const uploadRes = await fetch(`/api/metaweb/assignments/${assignment.id}/files`, {
					method: 'POST',
					headers: {
						Authorization: `Bearer ${localStorage.token}`
					},
					body: formData
				});

				if (!uploadRes.ok) {
					console.error('Failed to upload files');
				}
			}

			toast.success(
				isDraft
					? $i18n.t('Assignment saved as draft')
					: $i18n.t('Assignment published successfully')
			);

			goto(`/workspace/assignments/${assignment.id}`);
		} catch (error) {
			console.error('Error creating assignment:', error);
			toast.error($i18n.t('Failed to create assignment'));
		} finally {
			loading = false;
			uploading = false;
		}
	};

	// Save as draft
	const saveDraft = () => createAssignment(true);

	// Publish assignment
	const publishAssignment = () => createAssignment(false);

	// Cancel
	const cancel = () => {
		goto('/workspace/assignments');
	};
</script>

<svelte:head>
	<title>{$i18n.t('Create Assignment')} | {$i18n.t('Open WebUI')}</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="p-6 border-b border-gray-200 dark:border-gray-700">
		<button
			class="text-blue-600 dark:text-blue-400 hover:underline mb-2 flex items-center gap-1"
			on:click={cancel}
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
			{$i18n.t('Back to Assignments')}
		</button>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
			{$i18n.t('Create Assignment')}
		</h1>
		<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
			{$i18n.t('Create a new assignment for your students')}
		</p>
	</div>

	<!-- Form -->
	<div class="flex-1 overflow-y-auto p-6">
		<form class="max-w-3xl mx-auto space-y-6">
			<!-- Title -->
			<div>
				<label for="title" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Title')} <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					id="title"
					bind:value={title}
					placeholder={$i18n.t('Enter assignment title')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
					required
				/>
			</div>

			<!-- Description -->
			<div>
				<label for="description" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Description')}
				</label>
				<textarea
					id="description"
					bind:value={description}
					rows="6"
					placeholder={$i18n.t('Enter assignment description')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 resize-none"
				></textarea>
			</div>

			<!-- Subject and Grade Level -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label for="subject" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Subject')} <span class="text-red-500">*</span>
					</label>
					<select
						id="subject"
						bind:value={subject}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						required
					>
						<option value="">{$i18n.t('Select subject')}</option>
						{#each subjects as subj}
							<option value={subj.value}>{subj.label}</option>
						{/each}
					</select>
				</div>

				<div>
					<label for="gradeLevel" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Grade Level')} <span class="text-red-500">*</span>
					</label>
					<select
						id="gradeLevel"
						bind:value={gradeLevel}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						required
					>
						<option value="">{$i18n.t('Select grade level')}</option>
						{#each gradeLevels as level}
							<option value={level.value}>{level.label}</option>
						{/each}
					</select>
				</div>
			</div>

			<!-- Due Date and Total Points -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label for="dueDate" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Due Date')} <span class="text-red-500">*</span>
					</label>
					<input
						type="datetime-local"
						id="dueDate"
						bind:value={dueDate}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						required
					/>
				</div>

				<div>
					<label for="totalPoints" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Total Points')} <span class="text-red-500">*</span>
					</label>
					<input
						type="number"
						id="totalPoints"
						bind:value={totalPoints}
						min="1"
						max="1000"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						required
					/>
				</div>
			</div>

			<!-- Grading Mode -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Grading Mode')} <span class="text-red-500">*</span>
				</label>
				<div class="space-y-2">
					{#each gradingModes as mode}
						<label
							class="flex items-start p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 {gradingMode ===
							mode.value
								? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
								: ''}"
						>
							<input
								type="radio"
								name="gradingMode"
								value={mode.value}
								bind:group={gradingMode}
								class="mt-1 mr-3"
							/>
							<div>
								<div class="font-medium text-gray-900 dark:text-white">{mode.label}</div>
								<div class="text-sm text-gray-600 dark:text-gray-400">{mode.description}</div>
							</div>
						</label>
					{/each}
				</div>
			</div>

			<!-- Grading Rubric -->
			<div>
				<label for="gradingRubric" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Grading Rubric')} ({$i18n.t('Optional')})
				</label>
				<textarea
					id="gradingRubric"
					bind:value={gradingRubric}
					rows="4"
					placeholder={$i18n.t('Enter grading criteria and scoring details')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 resize-none"
				></textarea>
			</div>

			<!-- Late Submission Settings -->
			<div class="border border-gray-300 dark:border-gray-600 rounded-lg p-4 space-y-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="font-medium text-gray-900 dark:text-white">
							{$i18n.t('Allow Late Submission')}
						</div>
						<div class="text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Allow students to submit after due date')}
						</div>
					</div>
					<label class="relative inline-flex items-center cursor-pointer">
						<input type="checkbox" bind:checked={allowLateSubmission} class="sr-only peer" />
						<div
							class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"
						></div>
					</label>
				</div>

				{#if allowLateSubmission}
					<div>
						<label for="latePenalty" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('Late Penalty')} (%)
						</label>
						<input
							type="number"
							id="latePenalty"
							bind:value={latePenaltyPercent}
							min="0"
							max="100"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('Percentage deducted from final score for late submissions')}
						</p>
					</div>
				{/if}
			</div>

			<!-- File Attachments -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Attachments')} ({$i18n.t('Optional')})
				</label>

				<!-- File Upload Button -->
				<div class="mb-3">
					<input
						type="file"
						id="fileInput"
						on:change={handleFileSelect}
						multiple
						class="hidden"
					/>
					<button
						type="button"
						on:click={() => document.getElementById('fileInput').click()}
						class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition flex items-center gap-2"
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
								d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"
							/>
						</svg>
						{$i18n.t('Add Attachment')}
					</button>
				</div>

				<!-- File List -->
				{#if files.length > 0}
					<div class="space-y-2">
						{#each files as file, index}
							<div
								class="flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg"
							>
								<div class="flex items-center gap-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-5 h-5 text-gray-500"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
										/>
									</svg>
									<div>
										<div class="text-sm font-medium text-gray-900 dark:text-white">
											{file.name}
										</div>
										<div class="text-xs text-gray-500 dark:text-gray-400">
											{formatFileSize(file.size)}
										</div>
									</div>
								</div>
								<button
									type="button"
									on:click={() => removeFile(index)}
									class="text-red-500 hover:text-red-700"
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
											d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
										/>
									</svg>
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Action Buttons -->
			<div class="flex gap-3 pt-6 border-t border-gray-200 dark:border-gray-700">
				<button
					type="button"
					on:click={cancel}
					disabled={loading || uploading}
					class="flex-1 px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition disabled:opacity-50"
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="button"
					on:click={saveDraft}
					disabled={loading || uploading}
					class="flex-1 px-6 py-3 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition disabled:opacity-50"
				>
					{loading || uploading ? $i18n.t('Saving...') : $i18n.t('Save as Draft')}
				</button>
				<button
					type="button"
					on:click={publishAssignment}
					disabled={loading || uploading}
					class="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
				>
					{loading || uploading ? $i18n.t('Publishing...') : $i18n.t('Publish Assignment')}
				</button>
			</div>
		</form>
	</div>
</div>
