package com.acme.billing.invoice;

import java.math.BigDecimal;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InvoiceService {
    @Autowired
    private InvoiceRepository repository;

    @Transactional
    public Invoice create(String customerId, BigDecimal total) {
        if (total.signum() < 0) {
            throw new IllegalArgumentException("total must be positive");
        }
        return repository.save(new Invoice(customerId, total));
    }
}
