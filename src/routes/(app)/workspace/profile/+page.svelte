<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let profile = null;
	let loading = true;
	let studentId = '';

	const fetchProfile = async () => {
		loading = true;
		try {
			const res = await fetch(`/api/metaweb/profiles/students/${studentId}/profile/summary`, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});

			if (!res.ok) throw new Error('Failed to fetch profile');
			profile = await res.json();
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

		// 学生只能查看自己,教师可以查看所有学生
		studentId = $user.role === 'student' ? $user.id : $user.id;
		await fetchProfile();
	});

	const getMasteryPercent = (count, total) => {
		if (!total) return 0;
		return Math.round((count / total) * 100);
	};
</script>

<svelte:head>
	<title>学生画像 | Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="p-6 border-b border-gray-100 dark:border-gray-800">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
			📊 学生画像
		</h1>
		<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
			AI自动分析生成的个人学习画像
		</p>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
			</div>
		{:else if profile}
			<!-- Summary Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
				<!-- Total Knowledge Points -->
				<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
					<div class="text-sm text-gray-600 dark:text-gray-400">总知识点</div>
					<div class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
						{profile.total_knowledge_points}
					</div>
					<div class="text-xs text-gray-500 mt-1">个</div>
				</div>

				<!-- Mastered -->
				<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-6 shadow">
					<div class="text-sm text-green-600 dark:text-green-400">已掌握</div>
					<div class="text-3xl font-bold text-green-700 dark:text-green-300 mt-2">
						{profile.mastered_count}
					</div>
					<div class="text-xs text-green-600 dark:text-green-400 mt-1">
						{getMasteryPercent(profile.mastered_count, profile.total_knowledge_points)}%
					</div>
				</div>

				<!-- Learning -->
				<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-6 shadow">
					<div class="text-sm text-yellow-600 dark:text-yellow-400">学习中</div>
					<div class="text-3xl font-bold text-yellow-700 dark:text-yellow-300 mt-2">
						{profile.learning_count}
					</div>
					<div class="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
						{getMasteryPercent(profile.learning_count, profile.total_knowledge_points)}%
					</div>
				</div>

				<!-- Weak -->
				<div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-6 shadow">
					<div class="text-sm text-red-600 dark:text-red-400">薄弱项</div>
					<div class="text-3xl font-bold text-red-700 dark:text-red-300 mt-2">
						{profile.weak_count}
					</div>
					<div class="text-xs text-red-600 dark:text-red-400 mt-1">
						{getMasteryPercent(profile.weak_count, profile.total_knowledge_points)}%
					</div>
				</div>
			</div>

			<!-- Quick Links -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<!-- Knowledge Points -->
				<button
					on:click={() => goto('/workspace/profile/knowledge-points')}
					class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow hover:shadow-lg transition text-left"
				>
					<div class="text-2xl mb-2">📚</div>
					<div class="text-lg font-semibold text-gray-900 dark:text-white">知识点详情</div>
					<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
						查看各科目知识点掌握情况
					</div>
				</button>

				<!-- Weak Points -->
				<button
					on:click={() => goto('/workspace/profile/weak-points')}
					class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow hover:shadow-lg transition text-left"
				>
					<div class="text-2xl mb-2">⚠️</div>
					<div class="text-lg font-semibold text-gray-900 dark:text-white">薄弱知识点</div>
					<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
						专项突破薄弱环节
					</div>
				</button>

				<!-- Reports -->
				<button
					on:click={() => goto('/workspace/profile/reports')}
					class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow hover:shadow-lg transition text-left"
				>
					<div class="text-2xl mb-2">📈</div>
					<div class="text-lg font-semibold text-gray-900 dark:text-white">学习报告</div>
					<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
						{profile.latest_report_date ? `最新报告: ${profile.latest_report_date}` : '暂无报告'}
					</div>
				</button>
			</div>

			<!-- Info -->
			{#if profile.total_knowledge_points === 0}
				<div class="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
					<div class="text-blue-800 dark:text-blue-200">
						💡 提示: AI秘书将在每晚23:00自动分析你的作业数据,生成学习画像。
					</div>
				</div>
			{/if}
		{:else}
			<div class="text-center text-gray-600 dark:text-gray-400 mt-8">
				暂无数据
			</div>
		{/if}
	</div>
</div>
