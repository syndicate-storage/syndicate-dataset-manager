# SDM: Syndicate Dataset Manager

Syndicate Dataset Manager (SDM) allows you to mount public datasets on Syndicate
easily.

Commands
========

- `mount` : mount a dataset
- `mmount` : mount multi-datasets
- `unmount` : unmount
- `munmount` : unmount multi
- `ls` : show public datasets available
- `ps` : show current mount status
- `clean` : clear mount states (local caches and ETC.)


Options
=======

- `--log` : set log level (Default: `info`)
- `--backend` : set backend (Default: `FUSE`)


Usage
=====

To list available datasets:
```
sdm ls
```

e.g.
```
$ sdm ls
+------------+------------------------------------------------------------+
|  DATASET   |                        DESCRIPTION                         |
+------------+------------------------------------------------------------+
| nanograv9y |            NANOGrav - Gravitational waves data             |
|  imicrobe  |    iMicrobe - Metagenomic samples for microbial ecology    |
|   ivirus   |       iVirus - Metagenomic samples for viral ecology       |
|   uhslc    | University of Hawaii Sea Level Center - Ocean Tide Dataset |
|   refseq   |       NCBI-REFSEQ - NCBI Reference Sequence Database       |
+------------+------------------------------------------------------------+
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

To list mount status:
```
sdm ps
```

e.g.
```
$ sdm ps
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

To show more verbose log messages:
```
sdm ps --log=debug
```
