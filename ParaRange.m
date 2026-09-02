function [FZ_High,FZ_Low,P_High,P_Low,IA_High,IA_Low,SA_High,SA_Low,V_High,V_Low] = ParaRange(FZ_Nom, P_Nom, IA_Nom, SA_Nom, V_Nom, type)
% Function creates a range for each variable to account for anomolies in
% test data
% 
if strcmp(type,'Cornering') || strcmp(type,'cornering');
    if FZ_Nom == 350;
        FZ_High = 375;
        FZ_Low = 315;
    elseif FZ_Nom == 250;
        FZ_High = 275;
        FZ_Low = 226;
    elseif FZ_Nom == 200;
        FZ_High = 225;
        FZ_Low = 175;
    elseif FZ_Nom == 150;
        FZ_High = 170;
        FZ_Low = 136;
    elseif FZ_Nom == 100;
        FZ_High = 115;
        FZ_Low = 80;
    elseif FZ_Nom == 50;
        FZ_High = 65;
        FZ_Low = 35;
    elseif isnan(FZ_Nom);
        FZ_High = inf;
        FZ_Low = -inf;

    end

    if P_Nom == 8;
        P_High = 8.99;
        P_Low = 7;
    elseif P_Nom == 10;
        P_High = 10.5;
        P_Low = 9.00;
    elseif P_Nom == 11;
        P_High = 11.5;
        P_Low = 10.51;
    elseif P_Nom == 12;
        P_High = 12.99;
        P_Low = 11.51;
    elseif P_Nom == 14;
        P_High = 15;
        P_Low = 13;
    end
    
    if 1==1;
        SA_High = 15
        SA_Low = -15;
    end
    
    if isreal(IA_Nom)
        IA_High = IA_Nom + 0.075;
        IA_Low = IA_Nom - 0.075;   
    else isnan(IA_Nom);
        IA_High = inf;
        IA_Low = -inf;
    end
    
    if isreal(V_Nom)
        V_High = V_Nom +2.5
        V_Low = V_Nom - 2.5
    end
    
    


elseif strcmp(type,'Brake') || strcmp(type,'brake') || strcmp(type,'Braking') || strcmp(type,'braking');
    if FZ_Nom == 350;
        FZ_High = 375;
        FZ_Low = 315;
    elseif FZ_Nom == 250;
        FZ_High = 275;
        FZ_Low = 226;
    elseif FZ_Nom == 200;
        FZ_High = 225;
        FZ_Low = 175;
    elseif FZ_Nom == 150;
        FZ_High = 170;
        FZ_Low = 136;
    elseif FZ_Nom == 100;
        FZ_High = 115;
        FZ_Low = 80;
    elseif FZ_Nom == 50;
        FZ_High = 65;
        FZ_Low = 35;
    end

    if P_Nom == 8;
        P_High = 8.99;
        P_Low = 7;
    elseif P_Nom == 10;
        P_High = 10.5;
        P_Low = 9.00;
    elseif P_Nom == 11;
        P_High = 11.5;
        P_Low = 10.51;
    elseif P_Nom == 12;
        P_High = 12.99;
        P_Low = 11.51;
    elseif P_Nom == 14;
        P_High = 15;
        P_Low = 13;
    end
    
    if SA_Nom == 0;
        SA_High = 0.1;
        SA_Low = -0.1;
    elseif SA_Nom == -3;
        SA_High = -2.9;
        SA_Low = -3.1;
    elseif SA_Nom == -6;
        SA_High = -5.9;
        SA_Low = -6.1;
    end
    
    if isreal(IA_Nom)
        IA_High = IA_Nom + 0.075;
        IA_Low = IA_Nom - 0.075;    
    end
    
    if isreal(V_Nom)
        V_High = V_Nom + 0.2;
        V_Low = V_Nom - 0.2;
    end
end
end
