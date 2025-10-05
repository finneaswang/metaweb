<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	
	export let show = false;
	export let assignmentTitle = '';
	export let assignmentDescription = '';
	
	const dispatch = createEventDispatcher();
	
	let userMessage = '';
	let chatHistory = [];
	let isLoading = false;
	
	// 示例提示
	const examplePrompts = [
		'这是一篇议论文作业,需要评估逻辑性、论证充分性和语言表达',
		'编程作业,重点看代码质量、功能完整性、注释规范',
		'数学题,评分维度包括解题思路、计算准确性、步骤完整性'
	];
	
	async function sendMessage() {
		if (!userMessage.trim()) return;
		
		const message = userMessage.trim();
		userMessage = '';
		
		chatHistory = [...chatHistory, { role: 'user', content: message }];
		isLoading = true;
		
		try {
			// 调用后端AI生成Rubric
			const response = await fetch('/api/v1/ai-grading/generate-rubric', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify({
					assignment_title: assignmentTitle,
					assignment_description: assignmentDescription,
					user_requirements: message,
					chat_history: chatHistory
				})
			});
			
			if (!response.ok) throw new Error('生成失败');
			
			const result = await response.json();
			
			chatHistory = [...chatHistory, { 
				role: 'assistant', 
				content: result.explanation,
				rubric: result.rubric_json 
			}];
			
		} catch (error) {
			console.error(error);
			toast.error('AI生成失败,请重试');
		} finally {
			isLoading = false;
		}
	}
	
	function applyRubric(rubric) {
		dispatch('apply', rubric);
		show = false;
		toast.success('已应用Rubric评分标准');
	}
	
	function useExample(prompt) {
		userMessage = prompt;
	}
</script>

{#if show}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-850 rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col">
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-semibold">🤖 AI生成评分标准</h3>
				<button 
					on:click={() => show = false}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				>
					✕
				</button>
			</div>
			
			<!-- Chat Area -->
			<div class="flex-1 overflow-y-auto p-4 space-y-4">
				{#if chatHistory.length === 0}
					<div class="text-center py-8 space-y-4">
						<div class="text-4xl">💬</div>
						<p class="text-gray-600 dark:text-gray-400">
							告诉AI你的作业类型和评分要求,我会帮你生成Rubric标准
						</p>
						<div class="space-y-2">
							<p class="text-sm text-gray-500">💡 试试这些:</p>
							{#each examplePrompts as prompt}
								<button
									on:click={() => useExample(prompt)}
									class="block w-full text-left px-4 py-2 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded text-sm transition"
								>
									{prompt}
								</button>
							{/each}
						</div>
					</div>
				{:else}
					{#each chatHistory as msg}
						<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
							<div class="max-w-[80%] {msg.role === 'user' 
								? 'bg-blue-600 text-white' 
								: 'bg-gray-100 dark:bg-gray-800'} rounded-lg p-3">
								<p class="text-sm whitespace-pre-wrap">{msg.content}</p>
								
								{#if msg.rubric}
									<div class="mt-3 pt-3 border-t border-white/20 dark:border-gray-700">
										<p class="text-xs font-semibold mb-2">生成的评分标准:</p>
										<div class="space-y-1 text-xs">
											{#each msg.rubric.criteria as criterion}
												<div class="flex justify-between">
													<span>{criterion.title}</span>
													<span class="opacity-75">权重: {criterion.weight}</span>
												</div>
											{/each}
										</div>
										<button
											on:click={() => applyRubric(msg.rubric)}
											class="mt-2 w-full px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-medium"
										>
											✓ 应用此标准
										</button>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				{/if}
				
				{#if isLoading}
					<div class="flex justify-start">
						<div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-3">
							<div class="flex items-center gap-2">
								<div class="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
								<span class="text-sm text-gray-600 dark:text-gray-400">AI思考中...</span>
							</div>
						</div>
					</div>
				{/if}
			</div>
			
			<!-- Input Area -->
			<div class="p-4 border-t border-gray-200 dark:border-gray-700">
				<div class="flex gap-2">
					<input
						type="text"
						bind:value={userMessage}
						on:keydown={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
						placeholder="描述你的评分要求..."
						class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
						disabled={isLoading}
					/>
					<button
						on:click={sendMessage}
						disabled={!userMessage.trim() || isLoading}
						class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-lg font-medium transition"
					>
						发送
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
