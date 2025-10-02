<script lang="ts">
	import { onMount, getContext } from "svelte";
	import { user } from "$lib/stores";
	import { goto } from "$app/navigation";

	const i18n = getContext("i18n");

	let categories = [
		{ id: "math", name: "数学", icon: "🔢" },
		{ id: "programming", name: "编程", icon: "💻" },
		{ id: "language", name: "语言", icon: "📚" },
		{ id: "science", name: "科学", icon: "🔬" }
	];

	let selectedCategory = "";
	let score = 5;
	let reflection = "";
	let submitting = false;
	let aiFeedback = "";

	onMount(() => {
		if (!$user) {
			goto("/auth");
		}
	});

	const submitEvaluation = async () => {
		if (!selectedCategory || !reflection.trim()) {
			alert("请选择类别并填写反思内容");
			return;
		}

		try {
			submitting = true;
			const token = localStorage.getItem("token");

			const response = await fetch("/api/v1/evaluation/submit", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${token}`
				},
				body: JSON.stringify({
					category: selectedCategory,
					score: score,
					reflection: reflection
				})
			});

			if (response.ok) {
				const data = await response.json();
				aiFeedback = data.ai_feedback || "评估已提交，感谢你的反思！";
				
				// 重置表单
				selectedCategory = "";
				score = 5;
				reflection = "";
			} else {
				alert("提交失败，请稍后重试");
			}
		} catch (error) {
			console.error("Failed to submit evaluation:", error);
			alert("提交失败，请检查网络连接");
		} finally {
			submitting = false;
		}
	};
</script>

<div class="p-8 max-w-4xl mx-auto">
	<h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">自我评估</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-8">
		反思你的学习过程，AI会给你专业的反馈和建议
	</p>

	{#if aiFeedback}
		<div class="mb-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-6">
			<h3 class="text-lg font-semibold text-green-900 dark:text-green-100 mb-2 flex items-center gap-2">
				<span>✨</span> AI反馈
			</h3>
			<p class="text-green-700 dark:text-green-300 whitespace-pre-wrap">
				{aiFeedback}
			</p>
			<button
				on:click={() => (aiFeedback = "")}
				class="mt-4 text-sm text-green-600 dark:text-green-400 hover:underline"
			>
				继续评估
			</button>
		</div>
	{:else}
		<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
			<div class="space-y-6">
				<!-- 类别选择 -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
						选择评估类别 *
					</label>
					<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
						{#each categories as category}
							<button
								on:click={() => (selectedCategory = category.id)}
								class="flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition
											{selectedCategory === category.id
									? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
									: "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"}"
							>
								<span class="text-3xl">{category.icon}</span>
								<span
									class="text-sm font-medium {selectedCategory === category.id
										? "text-blue-600 dark:text-blue-400"
										: "text-gray-700 dark:text-gray-300"}"
								>
									{category.name}
								</span>
							</button>
						{/each}
					</div>
				</div>

				<!-- 自评分数 -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						自评分数: {score}/10
					</label>
					<input
						type="range"
						min="1"
						max="10"
						bind:value={score}
						class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
					/>
					<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
						<span>较弱</span>
						<span>一般</span>
						<span>较强</span>
					</div>
				</div>

				<!-- 反思内容 -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						学习反思 *
					</label>
					<textarea
						bind:value={reflection}
						rows="8"
						placeholder="请描述你在这个领域的学习过程、遇到的挑战、收获以及需要改进的地方..."
						class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
					/>
					<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
						💡 提示：详细的反思能让AI给出更精准的建议
					</p>
				</div>

				<!-- 提交按钮 -->
				<button
					on:click={submitEvaluation}
					disabled={submitting}
					class="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition"
				>
					{submitting ? "提交中..." : "提交评估"}
				</button>
			</div>
		</div>

		<!-- 说明卡片 -->
		<div class="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
			<h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
				📝 如何进行有效的自我评估？
			</h3>
			<ul class="space-y-2 text-blue-700 dark:text-blue-300 text-sm">
				<li>• 诚实地评估自己的能力水平</li>
				<li>• 具体描述学习过程中的困难和突破</li>
				<li>• 思考为什么某些内容难以理解</li>
				<li>• 列出具体的改进目标</li>
			</ul>
		</div>
	{/if}
</div>
