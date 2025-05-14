<script lang="ts">
  import Button from "./ui/button/button.svelte";
  import Input from "./ui/input/input.svelte";
  import Card from "./ui/card/card.svelte";
  let ip = "";
  let status: any = null;
  let artImages: any[] = [];
  let file: File | null = null;
  let loading = false;

  // Fonctions à implémenter plus tard
  async function getStatus() {}
  async function togglePower() {}
  async function toggleArtMode() {}
  async function uploadImage() {}
  async function fetchArtImages() {}
  async function deleteArtImage(content_id: string) {}
</script>

<Card class="max-w-xl mx-auto mt-8 p-6 bg-white">
  <h2 class="text-xl font-bold mb-4">Panneau de contrôle TV Samsung</h2>
  <div class="flex gap-2 mb-4">
    <Input placeholder="Adresse IP de la TV" bind:value={ip} class="flex-1" />
    <Button on:click={() => getStatus()} variant="secondary">Statut</Button>
    <Button on:click={() => togglePower()} variant="default">Power</Button>
    <Button on:click={() => toggleArtMode()} variant="outline">Art Mode</Button>
  </div>
  {#if status}
    <div class="mb-4">
      <pre class="bg-gray-100 p-2 rounded text-xs">{JSON.stringify(status, null, 2)}</pre>
    </div>
  {/if}
  <div class="mb-4">
    <label class="block mb-1 font-medium">Uploader une image</label>
    <input type="file" accept="image/*" on:change={(e: Event) => { const target = e.target as HTMLInputElement; file = target.files ? target.files[0] : null; }} class="mb-2" />
    <Button on:click={() => uploadImage()} disabled={!file || !ip}>Envoyer</Button>
  </div>
  <div>
    <div class="flex items-center justify-between mb-2">
      <span class="font-medium">Images Art</span>
      <Button on:click={() => fetchArtImages()} size="sm" variant="ghost">Rafraîchir</Button>
    </div>
    {#if artImages.length === 0}
      <p class="text-sm text-gray-500">Aucune image trouvée.</p>
    {:else}
      <ul class="space-y-2">
        {#each artImages as img}
          <li class="flex items-center justify-between bg-gray-50 p-2 rounded">
            <span class="truncate">{img.content_id}</span>
            <Button size="sm" variant="destructive" on:click={() => deleteArtImage(img.content_id)}>Supprimer</Button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</Card>

<style>
  :global(body) {
    background: #f7fafc;
  }
</style> 