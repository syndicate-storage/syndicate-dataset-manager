# SDM: Syndicate Dataset Manager

Syndicate Dataset Manager (SDM) allows you to mount public datasets on Syndicate 
easily.

Usage
=====

To list available datasets:
```
sdm list_datasets
```

e.g.
```
$ sdm list_datasets
+----------+------------------------------------------------------------+
| DATASET  |                        DESCRIPTION                         |
+----------+------------------------------------------------------------+
| imicrobe |    iMicrobe - Metagenomic samples for microbial ecology    |
|  ivirus  |       iVirus - Metagenomic samples for viral ecology       |
|  uhslc   | University of Hawaii Sea Level Center - Ocean Tide Dataset |
|  refseq  |       NCBI-REFSEQ - NCBI Reference Sequence Database       |
+----------+------------------------------------------------------------+
```

To mount a dataset:
```
sdm mount <dataset> [<mount_path>]
```

e.g.
```
$ sdm mount ivirus ~/ivirus
Registering a syndicate user, dc_anonymous_user@opencloud.us
Successfully registered a syndicate user, dc_anonymous_user@opencloud.us
Successfully reloaded a user cert, dc_anonymous_user@opencloud.us
Successfully reloaded a volume cert, ivirus
Successfully reloaded a gateway cert, ivirus_anonymous
Mounting syndicatefs, ivirus to /home/iychoi/ivirus
Successfully mounted syndicatefs, ivirus to /home/iychoi/ivirus

$ ls /home/iychoi/ivirus/
ABOR                            ExampleData              TOV_4_metaproteomes
Bioinfo_Class                   Freshwater_virophages    Vik_et_al_2017_data
Cellulophaga_Omics              GOV                      Virome_pipeline_benchmark
data                            Malspina_viral_proteins  VirSorter_curated_dataset
DNA_Viromes_library_comparison  TOV_43_viromes
```

To list mounts:
```
sdm show_mounts
```

e.g.
```
$ sdm show_mounts
+--------------+---------+---------------------+---------+
|   MOUNT_ID   | DATASET |      MOUNT_PATH     |  STATUS |
+--------------+---------+---------------------+---------+
| 1b9963913eb8 |  ivirus | /home/iychoi/ivirus | MOUNTED |
+--------------+---------+---------------------+---------+
```

To unmount:
```
sdm unmount <dataset OR mount_path OR mount_id> [<cleanup flag>]
```

`cleanup flag` is `boolean`. If `cleanup flag` is set `true`, `SDM` does not 
leave mount states including all configuration files and local caches.

e.g.
```
$ sdm unmount 1b99 false
Successfully unmounted syndicatefs, /home/iychoi/ivirus
```

To clean up `UNMOUNTED` mounts:
```
sdm clean
```
