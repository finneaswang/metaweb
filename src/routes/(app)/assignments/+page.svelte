<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { 
		getAssignments, 
		createNewAssignment,
		updateAssignmentById,
		deleteAssignmentById
	} from '$lib/apis/assignments';
	import {
		getSubmissionsByAssignmentId,
		createSubmission,
		getSubmissions,
		updateSubmissionById,
		submitSubmission as submitSubmissionAPI,
		gradeSubmission
	} from '$lib/apis/submissions';
	import { toast } from 'svelte-sonner';
    import AssignmentStatistics from '$lib/components/assignments/AssignmentStatistics.svelte';
    import RubricEditor from '$lib/components/assignments/RubricEditor.svelte';

	const i18n = getContext('i18n');

	let assignments = [];
	let mySubmissions = [];
	let currentView = 'list'; // list, create_assignment, view_assignment, submit, grade
	let selectedAssignment = null;
	let selectedSubmission = null;
	let assignmentSubmissions = [];
    let userRole = $user?.role || 'student';
	
	// 教师创建/编辑作业
	let assignmentForm = {
		title: '',
		description: '',
		content: '',
		due_date: '',
		max_score: 100,
t	ai_assist: false,
		rubric_json: { criteria: [] },
		status: 'draft'
	};
	
	// 学生提交内容
	let submissionContent = '';
	
	// 教师批改
	let gradeForm = {
		score: 0,
		grade: '',
		feedback: ''
	};

	let loading = true;

	onMount(async () => {
		if (!$user) {
			goto('/auth');
			return;
		}
		await loadData();
	});

	const loadData = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token');
			const assignmentsData = await getAssignments(token);
			if (assignmentsData) {
				assignments = assignmentsData;
			}
			
			if ($user?.role === 'student') {
				const submissionsData = await getSubmissions(token);
				if (submissionsData) {
					mySubmissions = submissionsData;
				}
			}
		} catch (error) {
			console.error('Failed to load data:', error);
			toast.error($i18n.t('Failed to load data'));
		} finally {
			loading = false;
		}
	};

	const showCreateAssignment = () => {
		assignmentForm = {
			title: '',
			description: '',
			content: '',
			due_date: '',
			max_score: 100,
			status: 'draft'
		};
		currentView = 'create_assignment';
	};

	const createAssignment = async () => {
		if (!assignmentForm.title || !assignmentForm.due_date) {
			toast.error($i18n.t('Please fill in required fields'));
			return;
		}

		try {
			const token = localStorage.getItem('token');
			await createNewAssignment(token, assignmentForm);
			toast.success($i18n.t('Assignment created'));
			await loadData();
			currentView = 'list';
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to create assignment'));
		}
	};

	const viewAssignment = async (assignment) => {
		selectedAssignment = assignment;
		
		if ($user?.role === 'teacher' || $user?.role === 'admin') {
			// 教师：加载该作业的所有提交
			try {
				const token = localStorage.getItem('token');
				const subs = await getSubmissionsByAssignmentId(token, assignment.id);
				assignmentSubmissions = subs || [];
			} catch (error) {
				console.error(error);
			}
			currentView = 'view_assignment';
		} else {
			// 学生：查看并准备提交
			const mySubmission = mySubmissions.find(s => s.assignment_id === assignment.id);
			selectedSubmission = mySubmission;
			submissionContent = mySubmission?.content || '';
			currentView = 'submit';
		}
	};

	const saveSubmission = async () => {
		try {
			const token = localStorage.getItem('token');
			
			if (!selectedSubmission) {
				// 创建新提交
				const result = await createSubmission(token, {
					assignment_id: selectedAssignment.id,
					content: submissionContent
				});
				selectedSubmission = result;
				toast.success($i18n.t('Submission saved as draft'));
			} else {
				// 更新现有提交
				await updateSubmissionById(token, selectedSubmission.id, {
					content: submissionContent
				});
				toast.success($i18n.t('Submission updated'));
			}
			
			await loadData();
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to save submission'));
		}
	};

	const submitSubmission = async () => {
		if (!selectedSubmission) {
			toast.error($i18n.t('Please save your work first'));
			return;
		}

		if (!confirm($i18n.t('Are you sure you want to submit? You cannot edit after submission.'))) {
			return;
		}

		try {
			const token = localStorage.getItem('token');
			await submitSubmissionAPI(token, selectedSubmission.id);
			toast.success($i18n.t('Submission submitted successfully'));
			await loadData();
			currentView = 'list';
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to submit'));
		}
	};

	const showGradeModal = (submission) => {
		selectedSubmission = submission;
		gradeForm = {
			score: submission.score || 0,
			grade: submission.grade || '',
			feedback: submission.feedback || ''
		};
		currentView = 'grade';
	};

	const submitGrade = async () => {
		try {
			const token = localStorage.getItem('token');
			await gradeSubmission(token, selectedSubmission.id, gradeForm);
			toast.success($i18n.t('Graded successfully'));
			await viewAssignment(selectedAssignment);
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to grade'));
		}
	};

	const deleteAssignment = async (id: string) => {
		if (!confirm($i18n.t('Are you sure?'))) return;

		try {
			const token = localStorage.getItem('token');
			await deleteAssignmentById(token, id);
			toast.success($i18n.t('Deleted'));
			await loadData();
		} catch (error) {
			console.error(error);
			toast.error($i18n.t('Failed to delete'));
		}
	};

	const getSubmissionForAssignment = (assignmentId: string) => {
		return mySubmissions.find(s => s.assignment_id === assignmentId);
	};

	const getStatusBadge = (status: string) => {
		const badges = {
			draft: 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300',
			submitted: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
			graded: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
		};
		return badges[status] || badges.draft;
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
					{#if $user?.role === 'teacher' || $user?.role === 'admin'}
						{$i18n.t('Create and manage assignments')}
					{:else}
						{$i18n.t('View and submit your assignments')}
					{/if}
				</p>
			</div>
			{#if currentView === 'list' && ($user?.role === 'teacher' || $user?.role === 'admin')}
				<button
					on:click={showCreateAssignment}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
				>
					{$i18n.t('Create Assignment')}
				</button>
			{:else if currentView !== 'list'}
				<button
					on:click={() => (currentView = 'list')}
					class="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-lg font-medium transition"
				>
					{$i18n.t('Back')}
				</button>
			{/if}
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="text-center py-12">
				<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
			</div>
		{:else if currentView === 'list'}
			<!-- Assignments List -->
			<div class="max-w-6xl mx-auto space-y-4">
				{#if assignments.length === 0}
					<div class="text-center py-12 text-gray-500 dark:text-gray-400">
						{$i18n.t('No assignments yet')}
					</div>
				{:else}
					{#each assignments as assignment (assignment.id)}
						<div
							class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6 hover:shadow-md transition cursor-pointer"
							on:click={() => viewAssignment(assignment)}
						>
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<div class="flex items-center gap-3 mb-2">
										<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
											{assignment.title}
										</h3>
										<span class="px-2 py-1 text-xs font-medium rounded-full {getStatusBadge(assignment.status)}">
											{assignment.status}
										</span>
										{#if $user?.role === 'student'}
											{@const mySubmission = getSubmissionForAssignment(assignment.id)}
											{#if mySubmission}
												<span class="px-2 py-1 text-xs font-medium rounded-full {getStatusBadge(mySubmission.status)}">
													{mySubmission.status === 'draft' ? '草稿' : mySubmission.status === 'submitted' ? '已提交' : '已批改'}
												</span>
												{#if mySubmission.score !== null && mySubmission.score !== undefined}
													<span class="text-sm font-medium text-green-600 dark:text-green-400">
														{mySubmission.score}/{mySubmission.max_score}
													</span>
												{/if}
											{/if}
										{/if}
									</div>
									<p class="text-gray-600 dark:text-gray-400 text-sm mb-2">
										{assignment.description || ''}
									</p>
									<div class="flex items-center gap-4 text-sm text-gray-500">
										<span>截止: {assignment.due_date}</span>
										{#if $user?.role === 'teacher' || $user?.role === 'admin'}
											<span>满分: {assignment.max_score}</span>
											<span>创建者: {assignment.teacher?.name || 'Unknown'}</span>
										{/if}
									</div>
								</div>
								{#if $user?.role === 'teacher' || $user?.role === 'admin'}
									<button
										on:click|stopPropagation={() => deleteAssignment(assignment.id)}
										class="px-3 py-1 text-sm bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 rounded transition"
									>
										删除
									</button>
								{/if}
							</div>
						</div>
					{/each}
				{/if}
			</div>
		{:else if currentView === 'create_assignment'}
			<!-- Create Assignment Form -->
			<div class="max-w-3xl mx-auto">
				<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
					<h2 class="text-xl font-semibold mb-4">{$i18n.t('Create New Assignment')}</h2>
					<div class="space-y-4">
						<div>
							<label class="block text-sm font-medium mb-2">标题 *</label>
							<input
								type="text"
								bind:value={assignmentForm.title}
								class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								placeholder="输入作业标题"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium mb-2">描述</label>
							<textarea
								bind:value={assignmentForm.description}
								rows="3"
								class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								placeholder="简短描述"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium mb-2">作业要求</label>
							<textarea
								bind:value={assignmentForm.content}
								rows="6"
								class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								placeholder="详细的作业要求和说明"
							/>
						</div>
						<div class="grid grid-cols-2 gap-4">
							<div>
								<label class="block text-sm font-medium mb-2">截止日期 *</label>
								<input
									type="date"
									bind:value={assignmentForm.due_date}
									class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium mb-2">满分</label>
								<input
									type="number"
									bind:value={assignmentForm.max_score}
									class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
									min="0"
								/>
							</div>
						</div>
						<!-- AI辅助评分选项 -->
						<div class="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
							<input
								type="checkbox"
								id="ai_assist"
								bind:checked={assignmentForm.ai_assist}
								class="w-4 h-4 text-blue-600 rounded"
							/>
							<label for="ai_assist" class="text-sm font-medium cursor-pointer">
								🤖 启用AI辅助评分
							</label>
						</div>

						<!-- Rubric编辑器 -->
						{#if assignmentForm.ai_assist}
							<div class="space-y-2">
								<label class="block text-sm font-medium">评分标准 (Rubric)</label>
								<RubricEditor 
									bind:rubric={assignmentForm.rubric_json}
									on:change={(e) => assignmentForm.rubric_json = e.detail}
								/>
							</div>
						{/if}
						<div class="flex gap-2 pt-4">
							<button
								on:click={createAssignment}
								class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
							>
								创建作业
							</button>
							<button
								on:click={() => (currentView = 'list')}
								class="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
							>
								取消
							</button>
						</div>
					</div>
				</div>
			</div>
		{:else if currentView === 'view_assignment'}
			<!-- Teacher View: Assignment Submissions -->
			<div class="max-w-6xl mx-auto">
				<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6 mb-4">
					<h2 class="text-2xl font-semibold mb-2">{selectedAssignment.title}</h2>
					<p class="text-gray-600 dark:text-gray-400 mb-4">{selectedAssignment.description}</p>
					{#if selectedAssignment.content}
						<div class="bg-gray-50 dark:bg-gray-900 p-4 rounded mb-4">
							<h3 class="text-sm font-medium mb-2">作业要求：</h3>
							<p class="text-sm whitespace-pre-wrap">{selectedAssignment.content}</p>
						</div>
					{/if}
					<div class="flex gap-4 text-sm text-gray-500">
						<span>截止: {selectedAssignment.due_date}</span>
						<span>满分: {selectedAssignment.max_score}</span>
						<span>提交数: {assignmentSubmissions.length}</span>
					</div>
				</div>

				<h3 class="text-lg font-semibold mb-3">学生提交</h3>
				<div class="space-y-3">

                <!-- Statistics Panel -->
                <AssignmentStatistics assignmentId={selectedAssignment.id} show={userRole === 'teacher' || userRole === 'admin'} />
					{#if assignmentSubmissions.length === 0}
						<div class="text-center py-8 text-gray-500">暂无提交</div>
					{:else}
						{#each assignmentSubmissions as submission (submission.id)}
							<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center gap-3 mb-2">
											<span class="font-medium">{submission.student?.name || 'Unknown'}</span>
											<span class="px-2 py-1 text-xs font-medium rounded-full {getStatusBadge(submission.status)}">
												{submission.status}
											</span>
											{#if submission.score !== null}
												<span class="text-sm font-medium text-green-600">
													{submission.score}/{submission.max_score}
												</span>
											{/if}
										</div>
										{#if submission.content}
											<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">{submission.content.substring(0, 100)}...</p>
										{/if}
										{#if submission.feedback}
											<p class="text-sm bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded">
												<span class="font-medium">反馈: </span>{submission.feedback}
											</p>
										{/if}
									</div>
									<button
										on:click={() => showGradeModal(submission)}
										class="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-400 rounded"
									>
										{submission.status === 'graded' ? '重新批改' : '批改'}
									</button>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</div>
		{:else if currentView === 'submit'}
			<!-- Student View: Submit Assignment -->
			<div class="max-w-4xl mx-auto">
				<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6 mb-4">
					<h2 class="text-2xl font-semibold mb-2">{selectedAssignment.title}</h2>
					<p class="text-gray-600 dark:text-gray-400 mb-4">{selectedAssignment.description}</p>
					{#if selectedAssignment.content}
						<div class="bg-gray-50 dark:bg-gray-900 p-4 rounded mb-4">
							<h3 class="text-sm font-medium mb-2">作业要求：</h3>
							<p class="text-sm whitespace-pre-wrap">{selectedAssignment.content}</p>
						</div>
					{/if}
					<div class="flex gap-4 text-sm text-gray-500">
						<span>截止: {selectedAssignment.due_date}</span>
						<span>满分: {selectedAssignment.max_score}</span>
					</div>
				</div>

				{#if selectedSubmission && selectedSubmission.status === 'graded'}
					<!-- Show graded submission -->
					<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
						<h3 class="text-lg font-semibold mb-4">你的提交（已批改）</h3>
						<div class="space-y-4">
							<div>
								<label class="block text-sm font-medium mb-2">提交内容：</label>
								<div class="bg-gray-50 dark:bg-gray-900 p-4 rounded">
									<p class="whitespace-pre-wrap">{selectedSubmission.content}</p>
								</div>
							</div>
							<div class="flex gap-6">
								<div>
									<span class="text-sm text-gray-500">得分：</span>
									<span class="text-xl font-bold text-green-600">{selectedSubmission.score}/{selectedSubmission.max_score}</span>
								</div>
								{#if selectedSubmission.grade}
									<div>
										<span class="text-sm text-gray-500">等级：</span>
										<span class="text-xl font-bold">{selectedSubmission.grade}</span>
									</div>
								{/if}
							</div>
							{#if selectedSubmission.feedback}
								<div>
									<label class="block text-sm font-medium mb-2">教师反馈：</label>
									<div class="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded">
										<p class="whitespace-pre-wrap">{selectedSubmission.feedback}</p>
									</div>
								</div>
							{/if}
						</div>
					</div>
				{:else if selectedSubmission && selectedSubmission.status === 'submitted'}
					<!-- Submitted but not graded -->
					<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
						<h3 class="text-lg font-semibold mb-4">你的提交（等待批改）</h3>
						<div class="bg-gray-50 dark:bg-gray-900 p-4 rounded">
							<p class="whitespace-pre-wrap">{selectedSubmission.content}</p>
						</div>
						<p class="text-sm text-gray-500 mt-4">已提交，等待教师批改</p>
					</div>
				{:else}
					<!-- Draft or new submission -->
					<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
						<h3 class="text-lg font-semibold mb-4">
							{selectedSubmission ? '编辑草稿' : '开始作业'}
						</h3>
						<div class="space-y-4">
							<div>
								<label class="block text-sm font-medium mb-2">你的答案：</label>
								<textarea
									bind:value={submissionContent}
									rows="12"
									class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
									placeholder="在这里输入你的答案..."
								/>
							</div>
							<div class="flex gap-2">
								<button
									on:click={saveSubmission}
									class="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
								>
									保存草稿
								</button>
								<button
									on:click={submitSubmission}
									class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
								>
									提交作业
								</button>
							</div>
						</div>
					</div>
				{/if}
			</div>
		{:else if currentView === 'grade'}
			<!-- Teacher: Grade Submission -->
			<div class="max-w-4xl mx-auto">
				<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6 mb-4">
					<h3 class="text-lg font-semibold mb-2">学生：{selectedSubmission.student?.name}</h3>
					<h4 class="text-sm text-gray-500 mb-4">作业：{selectedAssignment.title}</h4>
					<div class="bg-gray-50 dark:bg-gray-900 p-4 rounded">
						<p class="whitespace-pre-wrap">{selectedSubmission.content}</p>
					</div>
				</div>

				<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
					<h3 class="text-lg font-semibold mb-4">批改</h3>
					<div class="space-y-4">
						<div class="grid grid-cols-2 gap-4">
							<div>
								<label class="block text-sm font-medium mb-2">得分 *</label>
								<input
									type="number"
									bind:value={gradeForm.score}
									max={selectedAssignment.max_score}
									min="0"
									step="0.5"
									class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								/>
								<p class="text-xs text-gray-500 mt-1">满分: {selectedAssignment.max_score}</p>
							</div>
							<div>
								<label class="block text-sm font-medium mb-2">等级</label>
								<select
									bind:value={gradeForm.grade}
									class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								>
									<option value="">-</option>
									<option value="A">A</option>
									<option value="B">B</option>
									<option value="C">C</option>
									<option value="D">D</option>
									<option value="F">F</option>
								</select>
							</div>
						</div>
						<div>
							<label class="block text-sm font-medium mb-2">反馈</label>
							<textarea
								bind:value={gradeForm.feedback}
								rows="6"
								class="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
								placeholder="给学生的反馈和建议..."
							/>
						</div>
						<div class="flex gap-2 pt-4">
							<button
								on:click={submitGrade}
								class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium"
							>
								提交批改
							</button>
							<button
								on:click={() => viewAssignment(selectedAssignment)}
								class="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
							>
								取消
							</button>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
