<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let weakPoints = [];
	let loading = true;
	let studentId = '';

	const fetchWeakPoints = async () => {
		loading = true;
		try {
			const res = await fetch(`/api/metaweb/profiles/students/${studentId}/weak-points?threshold=0.5`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});

			if (!res.ok) throw new Error('Failed to fetch');
			weakPoints = await res.json();
		} catch (error) {
			console.error('Error:', error);
			toast.error('加载失败');
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (!$user) {
			goto('/');
			return;
		}

		studentId = $user.role === 'student' ? $user.id : $user.id;
		await fetchWeakPoints();
	});

	const formatDate = (dateStr) => {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('zh-CN');
	};

	const getUrgencyColor = (attempts, mastery) => {
		if (attempts >= 5 && mastery < 0.3) return 'border-red-500 bg-red-50 dark:bg-red-900/20';
		if (mastery < 0.3) return 'border-orange-500 bg-orange-50 dark:bg-orange-900/20';
		return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
	};

	const getUrgencyLabel = (attempts, mastery) => {
		if (attempts >= 5 && mastery < 0.3) return '🔴 紧急';
		if (mastery < 0.3) return '🟠 重要';
		return '🟡 关注';
	};
</script>

<svelte:head>
	<title>薄弱知识点 | Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="p-6 border-b border-gray-100 dark:border-gray-800">
		<div class="flex items-center gap-2 mb-4">
			<button
				on:click={() => goto('/workspace/profile')}
				class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
			>
				← 返回
			</button>
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
			⚠️ 薄弱知识点
		</h1>
		<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
			掌握度低于50%的知识点,建议重点突破
		</p>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
			</div>
		{:else if weakPoints.length > 0}
			<div class="space-y-4">
				{#each weakPoints as wp}
					<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow border-l-4 {getUrgencyColor(wp.total_attempts, wp.mastery_level)}">
						<div class="flex justify-between items-start mb-4">
							<div class="flex items-center gap-3">
								<span class="text-lg">{getUrgencyLabel(wp.total_attempts, wp.mastery_level)}</span>
								<span class="text-sm px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
									{wp.subject}
								</span>
								<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
									{wp.knowledge_point}
								</h3>
							</div>
						</div>

						<div class="grid grid-cols-2 md:grid-cols-5 gap-4">
							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">掌握度</div>
								<div class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
									{Math.round(wp.mastery_level * 100)}%
								</div>
							</div>

							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">练习次数</div>
								<div class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
									{wp.total_attempts}
								</div>
							</div>

							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">正确次数</div>
								<div class="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
									{wp.correct_attempts}
								</div>
							</div>

							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">首次遇到</div>
								<div class="text-sm text-gray-700 dark:text-gray-300 mt-1">
									{formatDate(wp.first_encountered)}
								</div>
							</div>

							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400">最近练习</div>
								<div class="text-sm text-gray-700 dark:text-gray-300 mt-1">
									{formatDate(wp.last_practiced)}
								</div>
							</div>
						</div>

						<!-- AI建议区域 (未来扩展) -->
						<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
							<div class="text-sm text-gray-600 dark:text-gray-400">
								💡 建议: 
								{#if wp.total_attempts < 3}
									需要更多练习来了解掌握情况
								{:else if wp.mastery_level < 0.3}
									建议从基础概念重新学习,可以寻求老师帮助
								{:else}
									继续练习,已经有所进步
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="text-center mt-8">
				<div class="text-6xl mb-4">🎉</div>
				<div class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
					太棒了!暂无薄弱知识点
				</div>
				<div class="text-gray-600 dark:text-gray-400">
					所有知识点掌握度都在50%以上,继续保持!
				</div>
			</div>
		{/if}
	</div>
</div>
