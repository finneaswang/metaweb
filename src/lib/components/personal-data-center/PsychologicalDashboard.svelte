<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';

	// 心理数据
	let psychologicalData = {
		weekly_chat_duration: 0,
		last_chat_date: null,
		mood_summary: '暂无数据',
		stress_level: 0,
		sleep_quality: '暂无数据',
		ai_suggestions: '暂无建议'
	};

	let loading = true;

	// 加载心理数据（从 PostgreSQL PDC 数据库）
	const loadData = async () => {
		loading = true;
		try {
			const res = await fetch('/api/v1/pdc/psychological/data', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const data = await res.json();
				if (data) {
					psychologicalData = {
						...psychologicalData,
						...data
					};
				}
			}
		} catch (error) {
			console.error('Failed to load psychological data:', error);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadData();
	});

	// 格式化时间
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
		if (level === 0) return '暂无评估';
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
	{:else}
		<!-- 概览卡片 -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			<!-- 本周聊天时长 -->
			<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">本周聊天时长</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
							{formatDuration(psychologicalData.weekly_chat_duration)}
						</p>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							目标: 10 分钟
						</p>
					</div>
					<div class="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-blue-600">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
						</svg>
					</div>
				</div>
			</div>

			<!-- 情绪状态 -->
			<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">情绪状态</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
							{psychologicalData.mood_summary}
						</p>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{psychologicalData.last_chat_date ? `最后更新: ${psychologicalData.last_chat_date}` : '暂无记录'}
						</p>
					</div>
					<div class="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-green-600">
							<path stroke-linecap="round" stroke-linejoin="round" d="M15.182 15.182a4.5 4.5 0 0 1-6.364 0M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75Zm-.375 0h.008v.015h-.008V9.75Zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75Zm-.375 0h.008v.015h-.008V9.75Z" />
						</svg>
					</div>
				</div>
			</div>

			<!-- 压力水平 -->
			<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">压力水平</p>
						<div class="flex items-baseline gap-2 mt-2">
							<p class="text-2xl font-semibold text-gray-900 dark:text-white">
								{psychologicalData.stress_level || 0}/5
							</p>
							<span class="text-sm px-2 py-0.5 rounded {getStressColor(psychologicalData.stress_level)}">
								{getStressText(psychologicalData.stress_level)}
							</span>
						</div>
					</div>
					<div class="w-12 h-12 {getStressColor(psychologicalData.stress_level)} rounded-full flex items-center justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
						</svg>
					</div>
				</div>
			</div>
		</div>

		<!-- 睡眠质量 -->
		<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">睡眠质量</h3>
			<p class="text-gray-700 dark:text-gray-300">
				{psychologicalData.sleep_quality || '暂无数据'}
			</p>
		</div>

		<!-- AI 建议 -->
		<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-6">
			<div class="flex items-start gap-3">
				<div class="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center flex-shrink-0">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-blue-600">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
					</svg>
				</div>
				<div class="flex-1">
					<h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">AI 心理健康建议</h3>
					<p class="text-blue-800 dark:text-blue-200">
						{psychologicalData.ai_suggestions || '暂无建议。请先与AI进行对话，系统会根据你的聊天内容生成个性化建议。'}
					</p>
				</div>
			</div>
		</div>

		<!-- 温馨提示 -->
		<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800 p-4">
			<div class="flex items-start gap-2">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-yellow-600 mt-0.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
				</svg>
				<div class="text-sm text-yellow-800 dark:text-yellow-200">
					<p class="font-medium mb-1">温馨提示</p>
					<p>如果你感到持续的情绪困扰或严重的心理压力，请及时联系学校心理咨询中心或专业心理咨询师寻求帮助。</p>
				</div>
			</div>
		</div>
	{/if}
</div>
