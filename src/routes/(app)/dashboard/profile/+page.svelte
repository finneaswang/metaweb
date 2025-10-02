<script lang="ts">
	import { onMount, getContext } from "svelte";
	import { user } from "$lib/stores";
	import { goto } from "$app/navigation";

	const i18n = getContext("i18n");

	let loading = true;
	let profileData = {
		strengths: [],
		weaknesses: [],
		recentProgress: [],
		suggestions: []
	};

	onMount(async () => {
		if (!$user) {
			goto("/auth");
			return;
		}
		await loadProfile();
	});

	const loadProfile = async () => {
		try {
			loading = true;
			// TODO: 调用后端API获取学习画像
			// 模拟数据
			profileData = {
				strengths: [
					{ name: "Python编程", score: 85, icon: "💻" },
					{ name: "数学基础", score: 78, icon: "🔢" }
				],
				weaknesses: [
					{ name: "算法思维", score: 62, icon: "🧩" },
					{ name: "英语阅读", score: 55, icon: "📚" }
				],
				recentProgress: [
					{ date: "2025-10-01", activity: "完成了Python作业", improvement: "+5%" },
					{ date: "2025-09-30", activity: "进行了数学自评", improvement: "+3%" }
				],
				suggestions: [
					"建议加强算法练习，可以从简单的排序算法开始",
					"每天阅读15分钟英文技术文章，提升专业词汇量",
					"定期进行自我评估，追踪学习进度"
				]
			};
		} catch (error) {
			console.error("Failed to load profile:", error);
		} finally {
			loading = false;
		}
	};
</script>

<div class="p-8 max-w-6xl mx-auto">
	<h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">学习画像</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-8">
		基于你的学习数据生成的个性化画像分析
	</p>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else}
		<!-- 技能雷达图区域 -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
			<!-- 优势项 -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
					<span>💪</span> 你的优势
				</h3>
				<div class="space-y-4">
					{#each profileData.strengths as strength}
						<div>
							<div class="flex items-center justify-between mb-2">
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
									<span>{strength.icon}</span>
									{strength.name}
								</span>
								<span class="text-sm font-semibold text-green-600 dark:text-green-400">
									{strength.score}%
								</span>
							</div>
							<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
								<div
									class="bg-green-500 h-2 rounded-full transition-all"
									style="width: {strength.score}%"
								></div>
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- 待提升项 -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
					<span>📈</span> 待提升项
				</h3>
				<div class="space-y-4">
					{#each profileData.weaknesses as weakness}
						<div>
							<div class="flex items-center justify-between mb-2">
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
									<span>{weakness.icon}</span>
									{weakness.name}
								</span>
								<span class="text-sm font-semibold text-orange-600 dark:text-orange-400">
									{weakness.score}%
								</span>
							</div>
							<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
								<div
									class="bg-orange-500 h-2 rounded-full transition-all"
									style="width: {weakness.score}%"
								></div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<!-- 最近进展 -->
		<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 mb-8">
			<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
				<span>📊</span> 最近进展
			</h3>
			<div class="space-y-3">
				{#each profileData.recentProgress as progress}
					<div class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
						<div class="flex-1">
							<p class="text-sm font-medium text-gray-900 dark:text-white">
								{progress.activity}
							</p>
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{progress.date}
							</p>
						</div>
						<span class="text-sm font-semibold text-green-600 dark:text-green-400">
							{progress.improvement}
						</span>
					</div>
				{/each}
			</div>
		</div>

		<!-- AI建议 -->
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
			<h3 class="text-xl font-semibold text-blue-900 dark:text-blue-100 mb-4 flex items-center gap-2">
				<span>✨</span> AI学习建议
			</h3>
			<ul class="space-y-3">
				{#each profileData.suggestions as suggestion}
					<li class="flex items-start gap-3 text-blue-700 dark:text-blue-300">
						<span class="text-lg mt-0.5">💡</span>
						<span class="flex-1">{suggestion}</span>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
