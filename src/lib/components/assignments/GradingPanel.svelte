<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	
	export let submission: any;
	export let assignment: any;
	export let aiGradeResult: any = null;  // AI评分结果
	export let loading = false;
	
	const dispatch = createEventDispatcher();
	
	// 初始化rubric分数
	let rubricScores = {};
	let feedback = '';
	let adoptAIDraft = false;
	
	$: if (aiGradeResult) {
		rubricScores = aiGradeResult.rubric_scores || {};
		feedback = aiGradeResult.feedback_draft || '';
	}
	
	// 如果有已保存的评分，加载它
	$: if (submission?.rubric_scores_json) {
		rubricScores = submission.rubric_scores_json;
	}
	$: if (submission?.feedback) {
		feedback = submission.feedback;
	}
	
	// 计算总分
	$: totalScore = calculateTotalScore();
	
	function calculateTotalScore() {
		if (!assignment?.rubric_json?.criteria) return 0;
		
		let weightedSum = 0;
		let totalWeight = 0;
		
		for (const criterion of assignment.rubric_json.criteria) {
			const score = rubricScores[criterion.id] || 0;
			const weight = criterion.weight || (1.0 / assignment.rubric_json.criteria.length);
			weightedSum += score * weight;
			totalWeight += weight;
		}
		
		// 转换为满分scale
		const normalized = totalWeight > 0 ? weightedSum / totalWeight : 0;
		return ((normalized / 5.0) * assignment.max_score).toFixed(2);
	}
	
	function submitGrade() {
		dispatch('grade', {
			rubric_scores: rubricScores,
			feedback: feedback,
			score: parseFloat(totalScore),
			adopt_ai_draft: adoptAIDraft
		});
	}
	
	function requestAIGrade() {
		dispatch('ai-grade');
	}
	
	function adoptAI() {
		adoptAIDraft = true;
		if (aiGradeResult) {
			rubricScores = { ...aiGradeResult.rubric_scores };
			feedback = aiGradeResult.feedback_draft;
		}
	}
</script>

<div class="grading-panel bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
	<h3 class="text-xl font-semibold mb-4">批改作业</h3>
	
	<!-- 学生答案 -->
	<div class="mb-6">
		<h4 class="font-medium mb-2">学生答案：</h4>
		<div class="p-4 bg-gray-50 dark:bg-gray-700 rounded border">
			{submission?.content || '（无内容）'}
		</div>
	</div>
	
	<!-- AI评分按钮 -->
	{#if assignment?.ai_assist && !aiGradeResult}
		<div class="mb-4">
			<button
				on:click={requestAIGrade}
				disabled={loading}
				class="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded disabled:opacity-50"
			>
				{loading ? 'AI评分中...': '🤖 AI自动评分'}
			</button>
		</div>
	{/if}
	
	<!-- AI评分结果 -->
	{#if aiGradeResult}
		<div class="mb-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-200">
			<div class="flex items-center justify-between mb-2">
				<h4 class="font-medium text-purple-700 dark:text-purple-300">
					🤖 AI评分建议
				</h4>
				<button
					on:click={adoptAI}
					class="px-3 py-1 text-sm bg-purple-500 hover:bg-purple-600 text-white rounded"
				>
					采纳AI建议
				</button>
			</div>
			<div class="text-sm">
				<p><strong>总分：</strong>{aiGradeResult.total_score} / {assignment.max_score}</p>
				<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
					置信度: {(aiGradeResult.confidence * 100).toFixed(0)}%
				</p>
			</div>
		</div>
	{/if}
	
	<!-- Rubric评分表 -->
	{#if assignment?.rubric_json?.criteria}
		<div class="mb-6">
			<h4 class="font-medium mb-3">评分标准（Rubric）：</h4>
			<div class="space-y-3">
				{#each assignment.rubric_json.criteria as criterion}
					<div class="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700 rounded">
						<div class="flex-1">
							<div class="font-medium">{criterion.title}</div>
							<div class="text-xs text-gray-500">
								ID: {criterion.id} | 权重: {criterion.weight || '平均'}
							</div>
						</div>
						<div class="flex items-center gap-2">
							<input
								type="number"
								bind:value={rubricScores[criterion.id]}
								min="0"
								max="5"
								step="0.5"
								class="w-20 px-2 py-1 border rounded text-center"
								placeholder="0-5"
							/>
							<span class="text-sm text-gray-500">/ 5</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
	
	<!-- 总分显示 -->
	<div class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
		<div class="flex items-center justify-between">
			<span class="font-medium">总分：</span>
			<span class="text-2xl font-bold text-blue-600 dark:text-blue-400">
				{totalScore} / {assignment?.max_score || 100}
			</span>
		</div>
	</div>
	
	<!-- 评语 -->
	<div class="mb-6">
		<label class="block font-medium mb-2">评语与反馈：</label>
		<textarea
			bind:value={feedback}
			rows="6"
			class="w-full px-3 py-2 border rounded resize-none"
			placeholder="请输入对学生作业的评语..."
		/>
	</div>
	
	<!-- 提交按钮 -->
	<div class="flex gap-3">
		<button
			on:click={submitGrade}
			class="flex-1 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded font-medium"
		>
			提交评分
		</button>
		<button
			on:click={() => dispatch('cancel')}
			class="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded"
		>
			取消
		</button>
	</div>
</div>

<style>
	.grading-panel :global(input),
	.grading-panel :global(textarea) {
		background-color: white;
	}
	:global(.dark) .grading-panel :global(input),
	:global(.dark) .grading-panel :global(textarea) {
		background-color: rgb(55 65 81);
		color: white;
	}
</style>
