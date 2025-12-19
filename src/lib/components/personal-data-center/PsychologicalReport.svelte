<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';

	let loading = true;
	let reports = [];

	// 加载历史报告（从 PostgreSQL）
	const loadReports = async () => {
		loading = true;
		try {
			const res = await fetch('/api/v1/pdc/psychological/reports', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				reports = await res.json();
			}
		} catch (error) {
			console.error('Failed to load reports:', error);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadReports();
	});

	// 格式化时长
	const formatDuration = (seconds) => {
		const mins = Math.floor(seconds / 60);
		return `${mins} 分钟`;
	};

	// 获取压力等级颜色
	const getStressColor = (level) => {
		if (level <= 2) return 'text-green-600 bg-green-100 dark:bg-green-900/30';
		if (level <= 3) return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30';
		return 'text-red-600 bg-red-100 dark:bg-red-900/30';
	};

	// 获取压力等级文本
	const getStressText = (level) => {
		if (level <= 2) return '轻度';
		if (level <= 3) return '中度';
		return '较高';
	};
</script>

<div class="space-y-6">
	{#if loading}
		<div class="flex justify-center items-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else if reports.length === 0}
		<!-- 空状态 -->
		<div class="text-center py-12">
			<div class="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 text-gray-400">
					<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
				</svg>
			</div>
			<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">暂无心理报告</h3>
			<p class="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
				完成每周的心理聊天后，系统会自动生成心理健康报告。开始与AI聊天吧！
			</p>
		</div>
	{:else}
		<!-- 报告列表 -->
		<div class="space-y-4">
			{#each reports as report}
				<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition">
					<!-- 报告头部 -->
					<div class="flex items-start justify-between mb-4">
						<div>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
								第{report.week_number}周 心理状态报告
							</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{report.year}年
							</p>
						</div>
						<button class="text-blue-600 hover:text-blue-700 text-sm font-medium">
							查看详情
						</button>
					</div>

					<!-- 关键指标 -->
					<div class="grid grid-cols-3 gap-4 mb-4">
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">情绪状态</p>
							<p class="text-sm font-medium text-gray-900 dark:text-white">{report.mood}</p>
						</div>
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">压力水平</p>
							<div class="flex items-center gap-1">
								<span class="text-sm font-medium text-gray-900 dark:text-white">{report.stress_level}/5</span>
								<span class="text-xs px-1.5 py-0.5 rounded {getStressColor(report.stress_level)}">
									{getStressText(report.stress_level)}
								</span>
							</div>
						</div>
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">聊天时长</p>
							<p class="text-sm font-medium text-gray-900 dark:text-white">{formatDuration(report.chat_duration)}</p>
						</div>
					</div>

					<!-- 总结 -->
					<div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 mb-3">
						<p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">本周总结</p>
						<p class="text-sm text-gray-600 dark:text-gray-400">{report.summary}</p>
					</div>

					<!-- 建议 -->
					<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
						<div class="flex items-start gap-2">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
							</svg>
							<div>
								<p class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">AI 建议</p>
								<p class="text-sm text-blue-800 dark:text-blue-200">{report.suggestions}</p>
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<!-- 导出按钮 -->
	<div class="flex justify-end">
		<button class="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition flex items-center gap-2">
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
				<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
			</svg>
			导出报告
		</button>
	</div>
</div>
