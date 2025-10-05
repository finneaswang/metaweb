<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	
	export let rubric = {
		criteria: [
			{ id: 'criterion1', title: '评分标准1', weight: 0.5, scale: [0, 1, 2, 3, 4, 5] }
		]
	};
	
	const dispatch = createEventDispatcher();
	
	const addCriterion = () => {
		const newId = `criterion${rubric.criteria.length + 1}`;
		rubric.criteria = [
			...rubric.criteria,
			{ 
				id: newId, 
				title: `评分标准${rubric.criteria.length + 1}`, 
				weight: 0.2, 
				scale: [0, 1, 2, 3, 4, 5] 
			}
		];
		dispatch('change', rubric);
	};
	
	const removeCriterion = (index) => {
		rubric.criteria = rubric.criteria.filter((_, i) => i !== index);
		dispatch('change', rubric);
	};
	
	const updateCriterion = () => {
		dispatch('change', rubric);
	};
</script>

<div class="rubric-editor border rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
	<div class="flex items-center justify-between mb-4">
		<h3 class="text-lg font-semibold">评分标准 (Rubric)</h3>
		<button
			type="button"
			on:click={addCriterion}
			class="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded"
		>
			+ 添加评分项
		</button>
	</div>
	
	<div class="space-y-4">
		{#each rubric.criteria as criterion, i}
			<div class="criterion-item border rounded p-3 bg-white dark:bg-gray-700">
				<div class="flex items-start gap-3">
					<div class="flex-1">
						<div class="grid grid-cols-2 gap-3 mb-2">
							<div>
								<label class="block text-sm font-medium mb-1">
									ID
								</label>
								<input
									type="text"
									bind:value={criterion.id}
									on:input={updateCriterion}
									class="w-full px-2 py-1 border rounded text-sm"
									placeholder="logic"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium mb-1">
									权重 (0-1)
								</label>
								<input
									type="number"
									bind:value={criterion.weight}
									on:input={updateCriterion}
									min="0"
									max="1"
									step="0.1"
									class="w-full px-2 py-1 border rounded text-sm"
								/>
							</div>
						</div>
						<div>
							<label class="block text-sm font-medium mb-1">
								标题
							</label>
							<input
								type="text"
								bind:value={criterion.title}
								on:input={updateCriterion}
								class="w-full px-2 py-1 border rounded text-sm"
								placeholder="逻辑性与结构"
							/>
						</div>
						<div class="mt-2 text-xs text-gray-500">
							评分范围: 0-5 分
						</div>
					</div>
					<button
						type="button"
						on:click={() => removeCriterion(i)}
						class="px-2 py-1 text-red-500 hover:text-red-700"
						title="删除"
					>
						✕
					</button>
				</div>
			</div>
		{/each}
	</div>
	
	{#if rubric.criteria.length === 0}
		<div class="text-center text-gray-500 py-8">
			暂无评分标准，点击"添加评分项"开始创建
		</div>
	{/if}
</div>

<style>
	.rubric-editor :global(input) {
		background-color: white;
	}
	:global(.dark) .rubric-editor :global(input) {
		background-color: rgb(55 65 81);
		color: white;
	}
</style>
