<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getStudentList, type StudentInfo } from '$lib/apis/teacher';
	import AIAssistantPanel from '$lib/components/teacher/AIAssistantPanel.svelte';

	let students: StudentInfo[] = [];
	let loading = true;
	let showAIAssistant = false;
	let selectedStudent: StudentInfo | null = null;

	onMount(async () => {
		await loadStudents();
	});

	const loadStudents = async () => {
		loading = true;
		try {
			students = await getStudentList(localStorage.token);
		} catch (error) {
			toast.error(`加载学生列表失败: ${error}`);
		} finally {
			loading = false;
		}
	};

	const openAIAssistant = (student: StudentInfo) => {
		selectedStudent = student;
		showAIAssistant = true;
	};

	const formatLastActive = (timestamp: number) => {
		if (!timestamp) return '从未登录';
		const date = new Date(timestamp * 1000);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const hours = Math.floor(diff / (1000 * 60 * 60));
		
		if (hours < 1) return '刚刚活跃';
		if (hours < 24) return `${hours} 小时前`;
		const days = Math.floor(hours / 24);
		if (days < 7) return `${days} 天前`;
		return date.toLocaleDateString('zh-CN');
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="px-6 py-4 border-b dark:border-gray-800">
		<h1 class="text-2xl font-semibold dark:text-gray-100">学生列表</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
			管理和查看学生学习情况
		</p>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-gray-100"></div>
			</div>
		{:else if students.length === 0}
			<div class="text-center py-12">
				<p class="text-gray-500 dark:text-gray-400">暂无学生</p>
			</div>
		{:else}
			<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
				<table class="w-full">
					<thead class="bg-gray-50 dark:bg-gray-900">
						<tr>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								姓名
							</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								邮箱
							</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								最后活跃
							</th>
							<th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								操作
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
						{#each students as student}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-900/50 transition">
								<td class="px-6 py-4 whitespace-nowrap">
									<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
										{student.name}
									</div>
								</td>
								<td class="px-6 py-4 whitespace-nowrap">
									<div class="text-sm text-gray-500 dark:text-gray-400">
										{student.email}
									</div>
								</td>
								<td class="px-6 py-4 whitespace-nowrap">
									<div class="text-sm text-gray-500 dark:text-gray-400">
										{formatLastActive(student.last_active_at)}
									</div>
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
									<button
										on:click={() => openAIAssistant(student)}
										class="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none transition"
									>
										💬 Ask AI
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>

<!-- AI Assistant Panel -->
{#if showAIAssistant && selectedStudent}
	<AIAssistantPanel 
		student={selectedStudent}
		on:close={() => {
			showAIAssistant = false;
			selectedStudent = null;
		}}
	/>
{/if}
