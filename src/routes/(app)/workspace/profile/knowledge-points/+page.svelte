<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let knowledgePoints = [];
	let loading = true;
	let studentId = '';
	let filterSubject = 'all';
	let filterMastery = 'all'; // all, mastered, learning, weak

	const subjects = ['数学', '物理', '化学', '英语', '语文', '生物', '历史', '地理'];

	const fetchKnowledgePoints = async () => {
		loading = true;
		try {
			let url = `/api/metaweb/profiles/students/${studentId}/knowledge-points?`;
			
			if (filterSubject !== 'all') url += `subject=${filterSubject}&`;
			
			if (filterMastery === 'mastered') {
				url += 'mastery_level_min=0.8';
			} else if (filterMastery === 'learning') {
				url += 'mastery_level_min=0.5&mastery_level_max=0.8';
			} else if (filterMastery === 'weak') {
				url += 'mastery_level_max=0.5';
			}

			const res = await fetch(url, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});

			if (!res.ok) throw new Error('Failed to fetch');
			knowledgePoints = await res.json();
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
		await fetchKnowledgePoints();
	});

	$: if (filterSubject || filterMastery) {
		fetchKnowledgePoints();
	}

	const getMasteryColor = (level) => {
		if (level >= 0.8) return 'text-green-600 dark:text-green-400';
		if (level >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	};

	const getMasteryLabel = (level) => {
		if (level >= 0.8) return '已掌握';
		if (level >= 0.5) return '学习中';
		return '薄弱';
	};

	const formatDate = (dateStr) => {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('zh-CN');
	};
</script>

<svelte:head>
	<title>知识点详情 | Open WebUI</title>
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
			📚 知识点掌握情况
		</h1>

		<!-- Filters -->
		<div class="flex gap-4 mt-4">
			<!-- Subject Filter -->
			<select
				bind:value={filterSubject}
				class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
			>
				<option value="all">全部科目</option>
				{#each subjects as subject}
					<option value={subject}>{subject}</option>
				{/each}
			</select>

			<!-- Mastery Filter -->
			<select
				bind:value={filterMastery}
				class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
			>
				<option value="all">全部掌握度</option>
				<option value="mastered">已掌握 (≥80%)</option>
				<option value="learning">学习中 (50-80%)</option>
				<option value="weak">薄弱 (&lt;50%)</option>
			</select>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
			</div>
		{:else if knowledgePoints.length > 0}
			<div class="space-y-4">
				{#each knowledgePoints as kp}
					<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
						<div class="flex justify-between items-start">
							<div class="flex-1">
								<div class="flex items-center gap-3">
									<span class="text-sm px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
										{kp.subject}
									</span>
									<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
										{kp.knowledge_point}
									</h3>
								</div>

								<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
									<div>
										<div class="text-sm text-gray-600 dark:text-gray-400">掌握度</div>
										<div class="text-xl font-bold {getMasteryColor(kp.mastery_level)} mt-1">
											{Math.round(kp.mastery_level * 100)}%
										</div>
										<div class="text-xs text-gray-500 mt-1">
											{getMasteryLabel(kp.mastery_level)}
										</div>
									</div>

									<div>
										<div class="text-sm text-gray-600 dark:text-gray-400">练习次数</div>
										<div class="text-xl font-bold text-gray-900 dark:text-white mt-1">
											{kp.total_attempts}
										</div>
										<div class="text-xs text-gray-500 mt-1">次</div>
									</div>

									<div>
										<div class="text-sm text-gray-600 dark:text-gray-400">正确次数</div>
										<div class="text-xl font-bold text-green-600 dark:text-green-400 mt-1">
											{kp.correct_attempts}
										</div>
										<div class="text-xs text-gray-500 mt-1">次</div>
									</div>

									<div>
										<div class="text-sm text-gray-600 dark:text-gray-400">首次遇到</div>
										<div class="text-sm text-gray-700 dark:text-gray-300 mt-1">
											{formatDate(kp.first_encountered)}
										</div>
										<div class="text-xs text-gray-500 mt-1">
											最近练习: {formatDate(kp.last_practiced)}
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="text-center text-gray-600 dark:text-gray-400 mt-8">
				暂无数据
			</div>
		{/if}
	</div>
</div>
