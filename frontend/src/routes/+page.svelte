<script lang="ts">
  import { onMount } from 'svelte';
  import Card from '$lib/components/ui/card/card.svelte';
  import Alert from '$lib/components/ui/alert/alert.svelte';
  import { goto } from '$app/navigation';
  import { tvService } from '$lib/services/tvService';
  import type { TV } from '$lib/services/tvService';
  import { Tv, MonitorOff, LoaderCircle } from 'lucide-svelte';

  let tvs: TV[] = [];
  let loading = true;
  let error = '';

  onMount(async () => {
    loading = true;
    error = '';
    try {
      tvs = await tvService.getAllTVs();
    } catch (e) {
      if (e instanceof Error) {
        error = e.message;
      } else {
        error = 'Erreur inconnue';
      }
    } finally {
      loading = false;
    }
  });

  function goToTV(tv: TV) {
    goto(`/tv/${tv.ip}`);
  }
</script>

<div class="min-h-screen bg-gray-50 flex flex-col items-center py-8 px-4 sm:py-12 sm:px-0">
  <div class="mb-6 sm:mb-8 flex flex-col items-center text-center">
    <Tv class="w-10 h-10 sm:w-12 sm:h-12 text-gray-400 mb-2" />
    <h1 class="text-xl sm:text-4xl font-bold">Samsung TV Controller</h1>
    <p class="text-sm sm:text-lg text-gray-500">Control your Samsung TVs</p>
  </div>
  {#if loading}
    <div class="flex justify-center my-6 sm:my-8"><LoaderCircle class="animate-spin w-6 h-6 sm:w-8 sm:h-8 text-gray-400" /></div>
  {:else if error}
    <Alert variant="destructive" class="mb-4 flex items-center gap-2">{error}</Alert>
  {:else if tvs.length === 0}
    <div class="text-center text-gray-400 my-6 sm:my-8">
      <MonitorOff class="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-2 text-gray-400" />
      No TV found
    </div>
  {:else}
    <div class="flex justify-center w-full max-w-xl px-2 md:px-0">
      <div class="flex flex-col gap-4 sm:gap-6 w-full max-w-3xl">
        {#each tvs as tv}
          <Card class="p-4 sm:p-8 bg-white shadow-md rounded-xl flex flex-col gap-3 sm:gap-4 cursor-pointer transition hover:bg-gray-100 active:bg-gray-200 w-full"
            on:click={() => goToTV(tv)}>
            <div class="flex items-center gap-3 sm:gap-4">
              <Tv class="w-8 h-8 sm:w-12 sm:h-12 text-gray-400" />
              <div>
                <div class="text-base sm:text-2xl font-bold">{tv.name || tv.ip}</div>
                <div class="text-gray-500 text-xs sm:text-sm">{tv.modelName} · {tv.ip}</div>
              </div>
            </div>
          </Card>
        {/each}
      </div>
    </div>
  {/if}
  <footer class="mt-6 sm:mt-8 text-xs text-gray-400">
    Make sure your TVs are on the same network
  </footer>
</div>

<style>
  .animate-spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    100% { transform: rotate(360deg); }
  }
</style>
