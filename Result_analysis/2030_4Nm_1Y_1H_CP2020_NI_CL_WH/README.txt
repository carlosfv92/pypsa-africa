An alternative clustering option was run (command m next to the number of clusters) to try and run capacity factors per powerplant.
However, there are issues with the current version of the code and it cannot run addequately the model with this command.
Isues are tracked up to the cluster_network script where no p_max_pu is assignated to the renewable powerplants (wind and solar) defined for each bus
