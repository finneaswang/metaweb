<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getAssignmentStatistics, exportAssignmentGrades, type AssignmentStatistics } from '$lib/apis/assignments';

	export let assignmentId: string;
	export let show: boolean = true;

	let statistics: AssignmentStatistics | null = null;
	let loading = true;
	let exporting = false;

	onMount(async () => {
		if (show) {
			await loadStatistics();
		}
	});

	$: if (show && assignmentId) {
		loadStatistics();
	}

	const loadStatistics = async () => {
		loading = true;
		try {
			statistics = await getAssignmentStatistics(localStorage.token, assignmentId);
		} catch (error) {
			toast.error(`加载统计失败: ${error}`);
		} finally {
			loading = false;
		}
	};

	const handleExport = async () => {
		exporting = true;
		try {
			const blob = await exportAssignmentGrades(localStorage.token, assignmentId);
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `assignment_${assignmentId}_grades.csv`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);
			toast.success('成绩已导出');
		} catch (error) {
			toast.error(`导出失败: ${error}`);
		} finally {
			exporting = false;
		}
	};
</script>

{#if show && !loading && statistics}
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6 mb-4">
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg font-semibold dark:text-gray-100">📊 作业统计</h3>
			<button
				on:click={handleExport}
				disabled={exporting}
				class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm disabled:opacity-50"
			>
				{exporting ? '导出中...': '📥 导出成绩'}
			</button>
		</div>

		<!-- Statistics Grid -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
			<!-- Submission Rate -->
			<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
				<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">提交率</div>
				<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
					{statistics.submission_rate}%
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">
					{statistics.submitted_count} / {statistics.total_students} 人
				</div>
			</div>

			<!-- Average Score -->
			<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
				<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">平均分</div>
				<div class="text-2xl font-bold text-green-600 dark:text-green-400">
					{statistics.avg_score}
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">
					已批改 {statistics.graded_count} 份
				</div>
			</div>

			<!-- Max Score -->
			<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
				<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">最高分</div>
				<div class="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
					{statistics.max_score}
				</div>
			</div>

			<!-- Min Score -->
			<div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
				<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">最低分</div>
				<div class="text-2xl font-bold text-red-600 dark:text-red-400">
					{statistics.min_score}
				</div>
			</div>
		</div>

		<!-- Grade Distribution -->
		<div class="border-t dark:border-gray-700 pt-4">
			<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">成绩分布</div>
			<div class="flex items-end space-x-4 h-32">
				{#each Object.entries(statistics.grade_distribution) as [grade, count]}
					<div class="flex-1 flex flex-col items-center">
						<div 
							class="w-full bg-blue-500 dark:bg-blue-600 rounded-t transition-all"
							style="height: {statistics.graded_count > 0 ? (count / statistics.graded_count * 100) : 0}%"
						/>
						<div class="text-xs font-medium mt-2 dark:text-gray-300">{grade}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{count}人</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{:else if show && loading}
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800 p-6 mb-4">
		<div class="flex justify-center items-center h-32">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"></div>
		</div>
	</div>
{/if}
