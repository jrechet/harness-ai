package com.acme.billing.invoice;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import java.math.BigDecimal;

@Entity
public class Invoice {
    @Id
    @GeneratedValue
    private Long id;
    private String customerId;
    private BigDecimal total;

    protected Invoice() { }

    public Invoice(String customerId, BigDecimal total) {
        this.customerId = customerId;
        this.total = total;
    }

    public Long getId() { return id; }
    public String getCustomerId() { return customerId; }
    public BigDecimal getTotal() { return total; }
}
